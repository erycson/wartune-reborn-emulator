"""Login no socket (20001) e carga inicial (8224) até a cena do castelo.

Sequência (ver ``docs/startup-sequence.md``):

1. 20001 ``LoginReqMsg`` -> troca de chave, 3841, 3 ``PlayerMsg``, 150 ``ArmyArmyMsg``.
   O primeiro ``PlayerMsg`` dispara LOGIN_SUCCESS e o cliente carrega os recursos.
2. 8224 com vários flags -> os 10 pacotes que ``LoginInitDataAccept`` espera.
3. 8224 ``user=true`` -> 112 (missões), 115 (itens, se houver), 4598, 150 e 6 ``LoginStateMsg``;
   o cliente escolhe a cena pelo ``noviceProcess`` (>= 19000 vai para o castelo).
"""

from __future__ import annotations

from google.protobuf.message import Message

from ...domain.errors import DomainError
from ...domain.models import PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from .. import rules, space
from ..builders import login as b
from ..builders import player as pb_player
from ..router import router
from ..session import LOGIN_CODE, GameSession

KEY_SIZE = 8

S_LOGIN_OK = 3841
S_PLAYER_INFO = 3
S_ARMY = 150
S_LOGIN_STATE = 6
S_LOGIN_SYNC_MAPID = 4598
S_CASTLE = 4153
S_CASTLE_TIME = 4452
S_BUILDINGS = 4154
S_BUILD_ORDERS = 4155
S_FRIENDS = 4156
S_FARM = 4157
S_SYS_PROPERTY = 4160
S_AAS = 4173
S_CHALLENGE_TIME = 4176
S_VERSION = 4233
S_SNS = 4245
S_QUESTS = 112
S_ITEMS = 115


def army(s: GameSession, snap: PlayerSnapshot) -> tuple[pb.ArmyArmyMsg, int]:
    leader, castle = snap.leader, snap.castle
    assert leader is not None and castle is not None and snap.character.id is not None
    stats = rules.leader_stats(snap, s.ctx.templates)
    hero = b.hero_info(leader, snap.character.id, stats)
    arm = rules.arm_avatar(snap, s.ctx.templates)
    return b.army_msg(snap, castle, hero, stats.fighting_capacity, arm), stats.fighting_capacity


def player_info(s: GameSession, snap: PlayerSnapshot) -> pb.PlayerMsg:
    from . import events  # events importa este módulo

    fighting = rules.leader_stats(snap, s.ctx.templates).fighting_capacity
    msg = b.player_msg(snap, fighting, s.ctx.clock.now(), rules.quest_bitmap(snap))
    events.fill_player(msg, snap, s.ctx.clock.now())
    return msg


def _send(s: GameSession, code: int, msg: Message | None = None) -> None:
    s.send(code, b.complete(msg) if msg is not None else None)


@router.on(LOGIN_CODE)
async def socket_login(s: GameSession, msg: pb.LoginReqMsg) -> None:
    if s.snapshot is not None:
        return
    if len(msg.ekeys) != KEY_SIZE:
        s.log.warning("20001 sem chave de sessão válida")
        s.connection.close()
        return
    # o cliente já trocou de chave logo após enviar o 20001: tudo daqui em diante usa a nova
    s.connection.rekey(bytes(k & 0xFF for k in msg.ekeys))
    try:
        character = await s.ctx.login.claim_socket(msg.key)
        # relogin: a sessão anterior termina (e grava) antes de carregarmos o snapshot; senão ela
        # gravaria depois por cima do que esta sessão fizer (item duplicado ou perdido)
        await s.ctx.online.kick(character.id or 0)
        snap = await s.ctx.characters.snapshot(character.id or 0)
    except DomainError as exc:
        s.log.info("login no socket recusado", erro=str(exc))
        s.connection.close()
        return
    except TimeoutError:
        s.log.warning("sessão anterior não terminou; login recusado", player=character.id)
        s.connection.close()
        return
    if snap.leader is None or snap.castle is None:
        s.log.error("personagem sem herói líder ou castelo", player=character.id)
        s.connection.close()
        return

    if s.ctx.online.get(snap.character.id or 0) is not None:  # dois 20001 juntos: o primeiro vence
        s.log.warning("login simultâneo do mesmo personagem; recusado", player=character.id)
        s.connection.close()
        return
    s.snapshot, s.login_key = snap, msg.key
    s.connection.client_id = s.player_id
    s.ctx.online.bind(s.player_id, s)
    s.log = s.log.bind(player=s.player_id)
    s.log.info("jogador entrou", nick=snap.character.nickname, novice=snap.character.novice_process)
    from . import events

    # primeiro login do dia (login acumulado, atividades de login) antes do PlayerMsg que mostra isso
    if changed := events.touch_login(snap, s.ctx.clock.now(), s.ctx.events):
        await s.ctx.characters.save(*changed)

    s.send(S_LOGIN_OK)
    _send(s, S_PLAYER_INFO, player_info(s, snap))
    _send(s, S_ARMY, army(s, snap)[0])


@router.on(8224)
async def login_load(s: GameSession, msg: pb.PlayerDataMsg) -> None:
    if msg.user:
        await _login_state(s)
        return
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    now = s.ctx.clock.now()
    if msg.sys:
        _send(s, S_VERSION, pb.VersionMsg())
        _send(s, S_SYS_PROPERTY, b.system_property(now, snap.server.opened_at))
        _send(s, S_CHALLENGE_TIME, pb.ChallengeCoolTimeMsg(totalCount=10, type=0, totalBuyCount=10))
    if msg.build:
        _send(s, S_BUILDINGS, b.buildings_msg(snap, snap.castle, s.ctx.templates))
        _send(s, S_BUILD_ORDERS, pb.BuildOrderList())
    if msg.castle:
        _send(s, S_CASTLE, b.castle_msg(snap, snap.castle))
        s.send(S_CASTLE_TIME, pb.BaseCastleMsg(defenceLefttime=0))  # oficial manda só este campo
    if msg.tree:
        _send(s, S_FARM, b.farm_msg(snap))
    if msg.friend:
        _send(s, S_FRIENDS, pb.FriendRelationList(maxPage=0, curPage=0))
    if msg.snsReq:
        _send(s, S_SNS, pb.SNSInfoMsg())
    if msg.aas:
        _send(s, S_AAS, pb.PlayerAASRefreshMsg(aasOnlineTime=0, isCloseAAS=True, sysSwitch=False))
    if msg.army:
        _send(s, S_ARMY, army(s, snap)[0])


async def _login_state(s: GameSession) -> None:
    # recarrega: o noviceProcess pode ter mudado via HTTP (updateplayernovice) depois do 20001
    s.snapshot = snap = await s.ctx.characters.snapshot(s.player_id)
    assert snap.castle is not None
    active = [q for q in snap.quests if not q.completed]
    s.send(S_QUESTS, pb_player.quest_update(active, rules.quest_bitmap(snap)))
    if snap.items:
        bag = pb.ItemMovedListMsg()
        for item in snap.items:
            bag.MergeFrom(pb_player.item_moved(item.bag_type, item.object_id, item.pos, item, s.player_id))
        s.send(S_ITEMS, bag)
    from . import events

    events.login_push(s)
    _send(s, S_LOGIN_SYNC_MAPID, pb.SimplePropertyMsg(param1=10000))
    _send(s, S_ARMY, army(s, snap)[0])
    _send(s, S_LOGIN_STATE, pb.LoginStateMsg(playerId=s.player_id, state=0))
    space.enter(s)  # o oficial cria a cidade do céu logo depois do 6
