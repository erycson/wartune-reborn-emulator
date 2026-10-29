"""Login no socket (20001) e carga inicial (8224) até a cena do castelo.

Sequência (ver ``docs/startup-sequence.md``):

1. 20001 ``LoginReqMsg`` -> troca de chave, 3841, 3 ``PlayerMsg``, 150 ``ArmyArmyMsg``.
   O primeiro ``PlayerMsg`` dispara LOGIN_SUCCESS e o cliente carrega os recursos.
2. 8224 com vários flags -> os 10 pacotes que ``LoginInitDataAccept`` espera.
3. 8224 ``user=true`` -> 112 (missões), 115 (itens, se houver), 4598, 150, 6 ``LoginStateMsg`` e 4151;
   o cliente escolhe a cena pelo ``noviceProcess`` (>= 19000 vai para o castelo).
"""

from __future__ import annotations

from google.protobuf.json_format import ParseDict
from google.protobuf.message import Message

from ...domain.errors import DomainError
from ...domain.models import PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from .. import arena_grupo, buffs, castle, daily, farm, guild, rewards, rules, social, space, timebox, torres
from .. import events as ev
from ..bag import expire as expire_items
from ..builders import login as b
from ..builders import player as pb_player
from ..builders.army import army_pawn_msg, castle_pawns
from ..router import router
from ..session import LOGIN_CODE, GameSession
from . import account, pet_defend, team, vehicle

KEY_SIZE = 8

S_LOGIN_OK = 3841
LOGIN_OTHER = 3842  # GatewayMsg (U_G_LOGIN_OTHER): BaseManager.__loginOtherHandler mostra notifyMsg e fecha o jogo
# TODO(inventado): sem captura nem texto no cliente; o título do alerta é o "public.prompt" do cliente
LOGIN_OTHER_TEXT = "Your account has logged in from another location."
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
S_EFFECT = 110
S_FRIENDS = 4156
S_FARM = 4157
S_SYS_PROPERTY = 4160
S_AAS = 4173
S_VERSION = 4233
S_SNS = 4245
S_QUESTS = 112
S_ITEMS = 115
S_WEDDING_ROOMS = 4662
S_ITEM_BUFFER = 4188  # pergaminhos de efeito ativos (game/buffs.py)
S_CASTLE_PAWNS = 100
# (visto) tutorial_en e oficial_20261023-215937-1: pacotes do login que só dizem "nada aqui" para sistemas que o
# servidor não tem (prosperidade do mundo, recuperar EXP, torre, questionário, eventos do dia, torre do rei, moedas)
S_PROSPERITY, S_RECOVER, S_TOWER_LIST, S_QUESTIONNAIRE = 4438, 4912, 4373, 4428
S_NOTICES, S_DAY_ACTION, S_SWITCH = 4251, 4393, 4422
S_CUSTOMER, S_HONOR_DAY, S_KING_TOWER, S_TOKENS = 4392, 4471, 4900, 4725
TOKEN_TYPES = (1, 2, 3, 4, 5, 12, 9, 22)  # (visto) 215937 #110, nessa ordem (PlayerCurrencyManager: cristal de pet...)


def tokens_msg(snap: PlayerSnapshot) -> pb.PlayerTokenInfoMsg:
    """4725 (``PlayerCurrencyManager``): só o Venus Crystal (12) tem saldo aqui; os outros vão zerados (visto)."""
    st = ev.peek(snap, rewards.ETERNAL_KEY)
    amount = {12: st.value if st is not None else 0}
    tokens = [pb.TokenInfoMsg(masterType=t, amount=amount.get(t, 0), expiredDate=b.NEVER) for t in TOKEN_TYPES]
    return pb.PlayerTokenInfoMsg(tokenInfos=tokens)


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
    cfg = s.ctx.world.settings.get("arena_party") or {}
    amethyst = ev.peek(snap, rewards.AMETHYST_KEY)
    msg.mineScore = amethyst.value if amethyst else 0  # playerInfo.mineral (loja de Amethyst)
    msg.crossScore = arena_grupo.points(ev.peek(snap, arena_grupo.KEY), now, cfg)  # pontos do PvpHeroFrame
    r = timebox.rule(s.ctx.world.settings)
    msg.timeProcess, msg.timeRun = timebox.box_state(snap.character, now, online=s.box_counting, r=r)
    msg.timeGet = msg.timeProcess > 0  # recebeu o último período alcançado (BoxManager)
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
        if (old := s.ctx.online.get(character.id or 0)) is not None:
            old.send(LOGIN_OTHER, pb.GatewayMsg(notifyMsg=LOGIN_OTHER_TEXT))  # o close envia a fila antes de fechar
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
    timebox.on_login(
        snap.character, now, timebox.rule(s.ctx.world.settings)
    )  # antes do PlayerMsg: timeRun e tempo offline
    rules.rest(snap.character, s.ctx.world.settings, timebox.offline_gp(snap.character))  # leaveGp do PlayerMsg
    from .player import army_tick  # player importa este módulo

    s.army_tick = army_tick(now)  # o login já manda 150/4434: o periódico só na próxima janela
    changed = castle.ensure(snap, s.ctx.templates, now)
    # o dia vira antes do PlayerMsg (stamina, energia e attackLeftCount já do dia) e grava junto: senão o 8224
    # recarrega o arena do banco com o dia de ontem
    changed.extend(daily.roll(snap, s.ctx.templates, now, s.ctx.world.settings))
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
        from . import arena  # arena importa este módulo

        arena.login(s, msg)  # 4176 do coliseu (um passo da carga) e do torneio
    if msg.build:
        _send(
            s,
            S_BUILDINGS,
            b.buildings_msg(snap, s.ctx.templates, impose_used=castle.impose_used(snap.castle, now)),
        )
        _send(s, S_BUILD_ORDERS, castle.order_list(snap, now))
        _send(s, S_POLITICS, castle.politics_msg(snap, s.ctx.templates))
        for kind, gold in castle.tech_effects(snap, s.ctx.templates):  # (só turco: login.json #20) 110 tipo 104 = 330
            s.send(S_EFFECT, pb.PropertyUpdatedMsg(propertyType=kind, value=gold))
    if msg.castle:
        truce = buffs.protection_left(snap, s.ctx.clock.now())
        _send(s, S_CASTLE, b.castle_msg(snap, snap.castle, truce))
        s.send(S_CASTLE_TIME, pb.BaseCastleMsg(defenceLefttime=truce))  # oficial manda só este campo
    if msg.army:
        _send(s, S_ARMY, army(s, snap)[0])
        # tropas do castelo: o oficial manda o 100 aqui, depois do 150, mesmo vazio para personagem sem tropas nem
        # quartel (tutorial_en #37-#39)
        s.send(S_CASTLE_PAWNS, castle_pawns(snap, s.ctx.templates))
        if snap.pets:  # só turco: login.json #30, entre o 100 e o 4438; sem pet o oficial não manda (tutorial_en)
            from .pets import S_PETS, pets_msg

            s.send(S_PETS, pets_msg(snap, s.ctx.templates))
        # (visto) 215937 #35 entre o 100 e o 4544; 0 = sem o buff de prosperidade no TopToolsBar (o servidor não tem)
        s.send(S_PROSPERITY, pb.SimplePropertyMsg(param1=0))
        from .systems import S_FATE, fate_list  # systems -> player -> login

        # destino: vazio no nível 1 (tutorial_en #42, depois do 150/100); com os tipos abertos só turco (login.json #34)
        s.send(S_FATE, fate_list(snap, s.ctx.templates))
        from . import tower, treasure  # tower importa campaign, que importa este módulo
        from .systems import S_DRAGON, dragon_list, open_dragon

        # (só turco: login.json #35-#37) guarda, mapa do tesouro e dragão depois do 4544
        tower.login_guard(s)
        treasure.login(s)
        if (dragon := dragon_list(open_dragon(snap))).fateInfo:  # o cliente nunca pede (sendDragonSoulRequest)
            s.send(S_DRAGON, dragon)
    # (visto) a ordem do oficial, que não segue a dos campos: 171155 #18-#63, 215937 #19-#64, 231733 #20-#67
    if msg.tree:
        from .marriage import ensure_tree  # marriage importa este módulo
        from .pets import guard_msg  # (só turco: login #49) o guarda, sem ``pos``

        await ensure_tree(s.ctx, snap)  # casado de antes da 0091 ganha a árvore do casal
        guard = guard_msg(snap, s.ctx.templates)
        _send(s, S_FARM, pb.LoadFarmRsp(farm=farm.farm_info(snap, now, s.ctx.templates, own=True, guard=guard)))
    if msg.star:
        from .stars import login_stars  # stars -> player -> login: import aqui evita o ciclo

        login_stars(s)
    if msg.powcardInfo:  # só turco: login.json #76 (nível 56); o inglês (nível 1, sem cartas, #24-#136) não manda 4905
        from .systems import S_CAMP_BUFFS, cards, send_cards

        if cards(rules.systems(snap)):
            s.send(S_CAMP_BUFFS, pb.PowCardBufListMsg())  # (só turco: login #75) vazio fora de campanha
            send_cards(s)
    if msg.tower:  # (visto) 215937 #48-#49, tutorial_en: 4912 e 4373 vazios; d27 #63: 4912 cheio (game/recover)
        from .. import recover

        s.send(S_RECOVER, recover.infos_msg(snap, s.ctx.templates, now))
        from .tower import login_list  # tower importa campaign, que importa este módulo

        s.send(S_TOWER_LIST, await login_list(s))
    if msg.questionnarie:  # (visto) 215937 #54: nenhum questionário
        s.send(S_QUESTIONNAIRE, pb.QuestionnarieInfoMsg())
    if msg.friend:
        for page in await social.friend_list(s):
            _send(s, S_FRIENDS, page)
    if msg.snsReq:
        _send(s, S_SNS, social.sns_info(snap.character, snap.sns))
    if msg.aas:
        _send(s, S_AAS, pb.PlayerAASRefreshMsg(aasOnlineTime=0, isCloseAAS=True, sysSwitch=False))
    # msg.offline: o oficial não manda o 4195 em captura nenhuma (inglesas com horas offline entre as sessões, login
    # turco com 13 milhões de leaveGp): com a chave 9 (LEAVE_GP) aberta o tempo offline vira EXP descansada
    # (``rules.rest``) e o 8287 fica sem uso
    if msg.active:  # (visto) 215937 #88-#89: os avisos do painel de atividades e o 4393 vazio
        notices = s.ctx.world.settings.get("active_notices") or []
        _send(s, S_NOTICES, ParseDict({"activeRspInfo": notices}, pb.ActiveRspMsg()))
        s.send(S_DAY_ACTION, pb.DayActiveRspMsg())
    if msg.switches:
        _send(s, S_SWITCH, switches_msg(s))
    if msg.challReward or msg.petChallengeReward or msg.crossScoreReward:
        from . import arena

        await arena.login_rewards(s, msg)


def switches_msg(s: GameSession) -> pb.SwitchInfoListMsg:
    """4422: as chaves do cliente (``BaseManager``, ``ConfigManager.info``) como o oficial (``game_settings.switches``,
    da 0078), menos as de ``closed_switches``: sistemas que o servidor não tem ficam fechados."""
    closed = set(s.ctx.world.settings.get("closed_switches") or ())
    rows = [
        dict(r, isOpen=bool(r["isOpen"]) and r["switchType"] not in closed)
        for r in s.ctx.world.settings.get("switches") or ()
    ]
    return ParseDict({"switches": rows}, pb.SwitchInfoListMsg())


async def _login_state(s: GameSession) -> None:
    # recarrega: o noviceProcess pode ter mudado via HTTP (updateplayernovice) depois do 20001
    s.snapshot = snap = await s.ctx.characters.snapshot(s.player_id)
    if account.expire_vice_reset(snap.character, s.ctx.clock.now()):
        await s.ctx.characters.save(snap.character)
    if gone := expire_items(snap, s.ctx.clock.now()):  # vencidos somem antes do 115 (dedução)
        await s.ctx.characters.save(delete=tuple(gone))
    assert snap.castle is not None
    # abertas e as repetíveis concluídas (com o ``completedDate``: o cliente conta o RepeatInterval por ela; só turco:
    # login.json #89 traz a 241 com a data antiga)
    active = [q for q in snap.quests if not q.completed or rules.is_repeat(s.ctx.templates, q.template_id)]
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
    s.send(S_WEDDING_ROOMS, pb.EngageMsg())  # salas de casamento: vazio, como o oficial (tutorial_en #43)
    pet_defend.login(s)  # 4686: invasão da ilha dos pets (tutorial_en #44, oficial_encantar #43)
    team.login(s)  # 4624 do time gravado (server_states); quem não está em time não recebe nada
    from .hero import login_rune  # hero importa player, que importa este módulo

    login_rune(s)  # (só turco: login.json #40) 4495 depois do 4686
    from . import events

    events.send_rate(s)  # 4247 logo depois do 4686 (tutorial_en #44-#45)
    if on := buffs.active(snap, s.ctx.clock.now()):  # (dedução) sem captura de login com pergaminho ativo
        _send(s, S_ITEM_BUFFER, buffs.buffer_list(on, s.ctx.clock.now()))
    await events.login_push(s)
    account.login_first(s)  # 4696 opType 6 logo antes do 4598
    _send(s, S_LOGIN_SYNC_MAPID, pb.SimplePropertyMsg(param1=10000))
    _send(s, S_ARMY, army(s, snap)[0])
    _send(s, S_LOGIN_STATE, pb.LoginStateMsg(playerId=s.player_id, state=0))
    # (visto) a cidade do céu logo depois do 6, antes do 4151, só depois do tutorial: oficial_20261023-171155-1
    # #92-#94 (noviceProcess 33000, exército no mapa 1); oficial_encantar #98-#99 (28500, exército na instância do
    # castelo) vai do 6 direto ao 4151, sem 4595 na sessão inteira
    if snap.character.novice_process > space.TUTORIAL_END:
        space.enter(s, show=False)
    from . import campaign, marriage  # os dois importam este módulo

    _send(s, campaign.S_RANK, campaign.ranks(s))  # tutorial_en #94; sem ele o mapa de campanhas quebra (AreaView)
    from .room import waiting_login  # room -> vip -> ... -> login

    waiting_login(s)  # 11 logo depois do 4151 (oficial_20261023-231733-1 #105)
    # (visto) 215937 #104-#105, #109-#110: canOpen 1 (sem leitor no cliente); honra do dia / teto (o geste não sobe
    # aqui); torre do rei (sem entradas na captura); as moedas de pet, cristal eterno, selo do rei e inspiração zeradas
    s.send(S_CUSTOMER, pb.FastOpenCustomerMsg(canOpen=1))
    s.send(S_HONOR_DAY, pb.SimplePropertyMsg(param1=0, param2=int(s.ctx.world.settings.get("honor_day_max", 0))))
    s.send(S_KING_TOWER, torres.king_msg(snap, s.ctx.clock.now()))  # as entradas de hoje e a maior dificuldade
    s.send(S_TOKENS, tokens_msg(snap))
    if (mc := ev.peek(snap, "mail_check")) is not None and mc.value == -1:  # e-mail verificado (mail.mail_check)
        s.send(337, b.complete(pb.MailCheckMsg(state=2, mail=mc.text)))  # TODO(inventado): sem captura do login
    from . import lords, warfield  # os dois importam este módulo

    # (visto) depois do 4725, não com o sys do 8224: tutorial_en #101-#106, 171155 #103-#108
    warfield.login(s)  # 4248: estado de cada campo pela agenda, nunca aberto
    lords.login(s)  # 4776: Senhores fechados

    await marriage.expire(s)  # noivado de mais de 20 dias cai antes do 4657
    if snap.marriage is not None:  # solteiro não recebe nada (tutorial_en #24-#136: nenhum 4657)
        _send(s, social.S_MARRIAGE, await social.marriage_msg(s.ctx, snap.marriage))
    space.present(s)  # (dedução) os outros depois do 4151; o oficial não manda 4597 no login (215937 #100-#106)
    guild.on_login(s)
