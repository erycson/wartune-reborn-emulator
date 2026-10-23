"""Login no socket (20001) e carga inicial (8224) até a cena do castelo.

Sequência (ver ``docs/startup-sequence.md``):

1. 20001 ``LoginReqMsg`` -> troca de chave, 3841, 3 ``PlayerMsg``, 150 ``ArmyArmyMsg``.
   O primeiro ``PlayerMsg`` dispara LOGIN_SUCCESS e o cliente carrega os recursos.
2. 8224 com vários flags -> os 10 pacotes que ``LoginInitDataAccept`` espera.
3. 8224 ``user=true`` -> 112 (missões), 115 (itens, se houver), 4598, 150, 6 ``LoginStateMsg`` e 4151;
   o cliente escolhe a cena pelo ``noviceProcess`` (>= 19000 vai para o castelo).
"""

from __future__ import annotations

from google.protobuf.message import Message

from ...domain.errors import DomainError
from ...domain.models import PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from .. import buffs, castle, daily, farm, guild, rules, social, space, timebox
from .. import events as ev
from ..bag import expire as expire_items
from ..builders import login as b
from ..builders import player as pb_player
from ..builders.army import army_pawn_msg, castle_pawns
from ..router import router
from ..session import LOGIN_CODE, GameSession
from . import account, vehicle

KEY_SIZE = 8

S_LOGIN_OK = 3841
S_PLAYER_INFO = 3
S_ARMY = 150
S_LOGIN_STATE = 6
S_LOGIN_SYNC_MAPID = 4598
S_FASHION_BOOK, S_SMITHY = 4542, 4184
S_CASTLE = 4153
S_CASTLE_TIME = 4452
S_BUILDINGS = 4154
S_BUILD_ORDERS = 4155
S_POLITICS = 152
S_FRIENDS = 4156
S_FARM = 4157
S_SYS_PROPERTY = 4160
S_AAS = 4173
S_VERSION = 4233
S_SNS = 4245
S_OFFLINE = 4195
S_QUESTS = 112
S_ITEMS = 115
S_PET_ISLAND_BOSS = 4686
S_WEDDING_ROOMS = 4662
S_ITEM_BUFFER = 4188  # pergaminhos de efeito ativos (game/buffs.py)
S_CASTLE_PAWNS = 100


def army(s: GameSession, snap: PlayerSnapshot) -> tuple[pb.ArmyArmyMsg, int]:
    leader, castle = snap.leader, snap.castle
    assert leader is not None and castle is not None and snap.character.id is not None
    templates = s.ctx.templates
    stats = rules.leader_stats(snap, templates, s.ctx.clock.now())
    rules.refresh_skill_point(leader, templates)  # derivado do nível e das skills (cache na coluna)
    hero = b.hero_info(leader, snap.character.id, stats, rules.talent_points(leader, templates))
    t = templates
    hero.wing, hero.hat = rules.avatar(snap, t, rules.WING), rules.avatar(snap, t, rules.HAT)
    hero.fashionArm = rules.avatar(snap, t, rules.FASHION_ARM)
    hero.fashionCloth = rules.avatar(snap, t, rules.FASHION_CLOTH)
    arm = rules.arm_avatar(snap, templates)
    pawn = army_pawn_msg(snap, templates, snap.character.id)
    mount: int | None = rules.systems(snap).mount_template or None
    rest = ev.peek(snap, "mount:rest")  # systems.MOUNT_REST_KEY; 0 explícito: o cliente só lê com hasMountTempId
    if mount and rest is not None and rest.value:
        mount = 0
    msg = b.army_msg(snap, castle, hero, stats.fighting_capacity, arm, pawn, mount)
    if pet := next((p for p in snap.pets if p.is_fight), None):  # o pet em batalha (só turco: login.json #5)
        msg.petTempId, msg.petQuqlity, msg.petName = pet.template_id, pet.quality, pet.name
    return msg, stats.fighting_capacity


def player_info(s: GameSession, snap: PlayerSnapshot) -> pb.PlayerMsg:
    from . import events  # events importa este módulo

    fighting = rules.leader_stats(snap, s.ctx.templates, s.ctx.clock.now()).fighting_capacity
    if snap.systems is not None:  # startFree certo mesmo para quem estava offline às 5h
        rules.refresh_star_day(snap.systems, s.ctx.clock.now())
    mine = s.ctx.guilds.of(snap.character.id or 0)
    now = s.ctx.clock.now()
    copies = snap.character.multi_copies(rules.copies_base(s.ctx.templates), now)  # o oficial não manda 4240 no login
    msg = b.player_msg(snap, fighting, now, rules.quest_bitmap(snap), copies, mine[0] if mine else None)
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
        character = await s.ctx.login.claim_socket(msg.key, s.connection.transport.peer.rsplit(":", 1)[0])
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
    now = s.ctx.clock.now()
    timebox.on_login(snap.character, now)  # antes do PlayerMsg: timeRun e tempo offline
    changed = castle.ensure(snap, s.ctx.templates, now)
    # o dia vira antes do PlayerMsg (stamina, energia e attackLeftCount já do dia) e grava junto: senão o 8224
    # recarrega o arena do banco com o dia de ontem
    changed.extend(daily.roll(snap, s.ctx.templates, now))
    s.snapshot, s.login_key = snap, msg.key
    s.connection.client_id = s.player_id
    s.ctx.online.bind(s.player_id, s)  # antes do primeiro await: o segundo 20001 junto já vê a sessão
    await s.ctx.characters.save(snap.character, *changed)
    from . import outer_city as oh

    await oh.refresh(s)  # mina do ciclo anterior vence antes do 109 e do 152
    s.log = s.log.bind(player=s.player_id)
    s.log.info("jogador entrou", nick=snap.character.nickname, novice=snap.character.novice_process)
    social.announce(s, online=True)
    from . import events

    # primeiro login do dia (login acumulado, atividades de login) antes do PlayerMsg que mostra isso
    if touched := events.touch_login(snap, s.ctx.clock.now()):
        await s.ctx.characters.save(*touched, *events.devotion_quests(s))  # o 112 vem no 8224 (user)

    s.send(S_LOGIN_OK)
    _send(s, S_PLAYER_INFO, player_info(s, snap))
    _send(s, S_ARMY, army(s, snap)[0])
    if touched:  # (visto) tutorial_en #16: devoção do login (leed 1) logo depois do PlayerMsg
        events.say_devotion(s)


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
        from . import arena, lords, warfield  # arena importa este módulo

        arena.login(s, msg)  # 4176 do coliseu (um passo da carga) e do torneio
        lords.login(s)  # 4776: Senhores fechados
        warfield.login(s)  # 4248: estado de cada campo pela agenda, nunca aberto
    if msg.build:
        _send(
            s,
            S_BUILDINGS,
            b.buildings_msg(snap, s.ctx.templates, impose_used=castle.impose_used(snap.castle, now)),
        )
        _send(s, S_BUILD_ORDERS, castle.order_list(snap, now))
        _send(s, S_POLITICS, castle.politics_msg(snap, s.ctx.templates))
    if msg.castle:
        _send(s, S_CASTLE, b.castle_msg(snap, snap.castle))
        s.send(S_CASTLE_TIME, pb.BaseCastleMsg(defenceLefttime=0))  # oficial manda só este campo
    if msg.tree:
        _send(s, S_FARM, pb.LoadFarmRsp(farm=farm.farm_info(snap, now, own=True)))
    if msg.friend:
        _send(s, S_FRIENDS, await social.friend_list(s))
    if msg.snsReq:
        _send(s, S_SNS, social.sns_info(snap.character, snap.sns))
    if msg.aas:
        _send(s, S_AAS, pb.PlayerAASRefreshMsg(aasOnlineTime=0, isCloseAAS=True, sysSwitch=False))
    if msg.army:
        _send(s, S_ARMY, army(s, snap)[0])
        # tropas do castelo: o oficial manda o 100 aqui, depois do 150, mesmo vazio para personagem sem tropas nem
        # quartel (tutorial_en #37-#39)
        s.send(S_CASTLE_PAWNS, castle_pawns(snap, s.ctx.templates))
        from .systems import S_FATE, fate_list  # systems -> player -> login

        # destino: vazio no nível 1 (tutorial_en #42, depois do 150/100); com os tipos abertos só turco (login.json #34)
        s.send(S_FATE, fate_list(snap, s.ctx.templates))
        if snap.pets:  # só turco: login.json #30; sem pet o oficial não manda (tutorial_en #24-#136: nenhum 4540)
            from .pets import S_PETS, pets_msg

            s.send(S_PETS, pets_msg(snap, s.ctx.templates))
    if msg.star:
        from .stars import login_stars  # stars -> player -> login: import aqui evita o ciclo

        login_stars(s)
    if msg.powcardInfo:  # só turco: login.json #76 (nível 56); o inglês (nível 1, sem cartas, #24-#136) não manda 4905
        from .systems import S_POWCARD, cards, powcard_msg

        if cards(rules.systems(snap)):
            s.send(S_POWCARD, powcard_msg(snap, s.ctx.templates, s.ctx.world.settings.get("powcard_suite_slots")))
    if msg.offline and (gp := timebox.offline_gp(snap.character)) > 0:  # conta nova: o oficial não manda
        _send(s, S_OFFLINE, pb.OfflineRewardMsg(offlineTime=snap.character.offline_seconds, gpCount=gp))
    if msg.challReward or msg.petChallengeReward or msg.crossScoreReward:
        from . import arena

        await arena.login_rewards(s, msg)


async def _login_state(s: GameSession) -> None:
    # recarrega: o noviceProcess pode ter mudado via HTTP (updateplayernovice) depois do 20001
    s.snapshot = snap = await s.ctx.characters.snapshot(s.player_id)
    if account.expire_vice_reset(snap.character, s.ctx.clock.now()):
        await s.ctx.characters.save(snap.character)
    if gone := expire_items(snap, s.ctx.clock.now()):  # vencidos somem antes do 115 (dedução)
        await s.ctx.characters.save(delete=tuple(gone))
    assert snap.castle is not None
    active = [q for q in snap.quests if not q.completed]
    s.send(S_QUESTS, pb_player.quest_update(active, rules.quest_bitmap(snap)))
    if snap.items:
        bag = pb.ItemMovedListMsg()
        for item in snap.items:
            bag.MergeFrom(pb_player.item_moved(item.bag_type, item.object_id, item.pos, item, s.player_id))
        s.send(S_ITEMS, bag)
    _send(s, S_FASHION_BOOK, pb_player.fashion_book(snap, s.ctx.templates))
    s.send(S_SMITHY, pb_player.smithy(s.ctx.templates))
    if snap.character.novice_process >= space.POST_TUTORIAL:  # conta nova não recebe (tutorial_en #24-#136: sem 4512)
        vehicle.login(s)  # o oficial manda antes e depois do 6; aqui antes, junto com o resto do estado
    # ilha dos pets: sem invasão do chefe em andamento (tutorial_en #44, todos os campos zerados)
    zero = dict.fromkeys(("leftTime", "mapId", "bossId", "peaceMiddle", "peaceHigh", "peaceBoss", "ragePoint"), 0)
    s.send(S_WEDDING_ROOMS, pb.EngageMsg())  # salas de casamento: vazio, como o oficial (tutorial_en #43)
    s.send(S_PET_ISLAND_BOSS, pb.PetIslandDefendStateMsg(**zero))
    from . import events

    events.send_rate(s)  # 4247 logo depois do 4686 (tutorial_en #44-#45)
    if on := buffs.active(snap, s.ctx.clock.now()):  # (dedução) sem captura de login com pergaminho ativo
        _send(s, S_ITEM_BUFFER, buffs.buffer_list(on, s.ctx.clock.now()))
    events.login_push(s)
    _send(s, S_LOGIN_SYNC_MAPID, pb.SimplePropertyMsg(param1=10000))
    _send(s, S_ARMY, army(s, snap)[0])
    _send(s, S_LOGIN_STATE, pb.LoginStateMsg(playerId=s.player_id, state=0))
    from . import campaign, marriage  # os dois importam este módulo

    _send(s, campaign.S_RANK, campaign.ranks(s))  # tutorial_en #94; sem ele o mapa de campanhas quebra (AreaView)

    await marriage.expire(s)  # noivado de mais de 20 dias cai antes do 4657
    if snap.marriage is not None:  # solteiro não recebe nada (tutorial_en #24-#136: nenhum 4657)
        _send(s, social.S_MARRIAGE, await social.marriage_msg(s.ctx, snap.marriage))
    space.enter(s)  # o oficial cria a cidade do céu logo depois do 6
    guild.on_login(s)
