# Tabela de pacotes

> Gerado por `tools/scan_opcodes.py` a partir do cliente decompilado. Não edite à mão.

Direção: **C→S** = o cliente envia (`new PackageOut`), **S→C** = o cliente escuta (`"SLGSocketEvent" + N`). Um mesmo opcode pode existir nas duas direções.

| Opcode | Hex | Nome(s) em ProtocolType | C→S (mensagem) | S→C (mensagem) |
|---:|---|---|---|---|
| 0 | 0x0000 | U_C_PET_REMOVE |  | (não lê corpo) |
| 3 | 0x0003 | U_C_PLAYER_INFO |  | PlayerMsg |
| 4 | 0x0004 | U_C_PLAYER_TIME |  | BoxBoxMsg |
| 6 | 0x0006 | U_C_PLAYER_LOGINSTATEE |  | LoginStateMsg |
| 11 | 0x000B | U_C_CAMPAIGN_WAITING_PLAYER_LIST |  | RoomPlayerListMsg |
| 12 | 0x000C | U_C_CAMPAIGN_ROOM_CREATE |  | RoomMsg |
| 13 | 0x000D | U_C_CAMPAIGN_ROOM_LIST |  | RoomListRspMsg |
| 15 | 0x000F | U_C_CAMPAIGN_ROOM_EXIT |  | RoomExitRspMsg |
| 16 | 0x0010 | U_C_CAMPAIGN_ROOM_INVITE |  | RoomInviteMsg |
| 17 | 0x0011 | U_C_CAMPAGIN_ROOM_PLACESTATE |  | PlaceStateRspMsg |
| 19 | 0x0013 | U_C_CAMPAIGN_FOG_UPDATE |  | CampaignFogUpdateMsg |
| 20 | 0x0014 | U_C_CAMPAIGN_SYSTEM_ARMY |  | SystemArmyMsg |
| 21 | 0x0015 | U_C_CAMPAIGN_ENTER |  | RoomEnterMsg |
| 22 | 0x0016 | U_C_CAMPAIGN_EXIT |  | CampaignExitMsg |
| 24 | 0x0018 | U_C_PLAYER_READY_STATE |  | PlayerReadyRspMsg |
| 25 | 0x0019 | U_C_ROOM_STATE |  | RoomStateRspMsg |
| 26 | 0x001A | U_C_CAMPAIGN_TAKE_CARD |  | CampaignTakeCardsMsg |
| 28 | 0x001C | U_C_CAMPAIGN_ROOM_KILLPLAYER |  | KillPlayerRspMsg |
| 29 | 0x001D | U_C_CAMPAIGN_CONFIRM |  | CampaignConfirmMsg |
| 32 | 0x0020 | U_C_CAMPAIGN_ROOM_EDIT |  | EditRoomRspMsg |
| 35 | 0x0023 | U_C_CONSORTIA_USERINVITE |  | ConsortiaMsg |
| 36 | 0x0024 | U_C_CONSORTIA_INVITEDEL |  | (não lê corpo) |
| 37 | 0x0025 | U_C_CONSORTIA_USERPASS |  | ConsortiaMsg |
| 40 | 0x0028 | U_C_CONSORTIA_PASS |  | (não lê corpo) |
| 41 | 0x0029 | U_C_CONSORTIA_INVITE |  | ConsortiaMsg |
| 42 | 0x002A | U_C_CONSORTIA_OFF |  | ConsortiaMsg |
| 45 | 0x002D | U_C_CONSORTIA_FRESHALTAR |  | ConsortiaMsg |
| 49 | 0x0031 | U_C_CONSORTIA_RENAME |  | ConsortiaRenameRspMsg |
| 50 | 0x0032 | U_C_CONSORTIA_DUTYUPDATE |  | ConsortiaMsg |
| 52 | 0x0034 | U_C_QUEST_FINISH |  | QuestFinishedRspMsg |
| 60 | 0x003C | U_C_HERO_SKILL_UPGRADE |  | UpdatedSkillMsg |
| 61 | 0x003D | U_C_HERO_SKILLPOINT_RESET |  | UpdatedSkillMsg |
| 64 | 0x0040 | U_C_HERO_SETFASTKEY |  | HeroFastKeyMsg |
| 69 | 0x0045 | U_B_USER_STOP |  | UserStopMsg |
| 72 | 0x0048 | U_B_USER_REINFORCE |  | ReinforceMsg |
| 75 | 0x004B | U_B_HERO_ORDER |  | HeroOrderMsg |
| 77 | 0x004D | U_B_FIGHT_MODE |  | AttackModeMsg |
| 78 | 0x004E | U_CH_ADD_RELATIONSHIP |  | FriendInfoMsg |
| 79 | 0x004F | U_CH_REMOVE_RELATIONSHIP |  | FriendRelationMsg |
| 83 | 0x0053 | U_CH_CHANNEL_CHA |  | ChatChannelMsg |
| 84 | 0x0054 | U_CH_FRIENDADD_CONFIRM |  | FriendRelationMsg |
| 85 | 0x0055 | U_CH_RECOMMENDLIST |  | RecommendListMsg |
| 86 | 0x0056 | U_C_ITEM_STRENGTHEN |  | StoreRspMsg |
| 89 | 0x0059 | U_C_ITEM_COMPOSE |  | StoreRspMsg |
| 90 | 0x005A | U_C_SHOP_BUY |  | ShopMsg |
| 92 | 0x005C | U_C_ARMY_RECRUITED |  | ArmyPawnUpdatedMsg |
| 93 | 0x005D | U_C_ARMY_EDIT |  | ArmyEditRspMsg |
| 98 | 0x0062 | U_C_ARMY_RETURNHOME |  | OutercityRspMsg |
| 100 | 0x0064 | U_C_ARMY_UPDATE_ARMYPAWN |  | ArmyPawnUpdatedMsg |
| 102 | 0x0066 | U_C_BUILDING_ORDER_QUICK |  | OrderQuickRspMsg |
| 103 | 0x0067 | U_C_BUILDING_UPENERGY |  | TransInfoMsg |
| 104 | 0x0068 | U_C_BUILDING_ORDERADD |  | OrderInfoMsg |
| 105 | 0x0069 | U_C_BUILDING_TRANSCASTLE |  | CastleReqMsg |
| 106 | 0x006A | U_C_TREE_PICK |  | TreeUpdateRsp |
| 108 | 0x006C | U_C_UNOCCPWILDLAND |  | GiveupWildLandMsg |
| 109 | 0x006D | U_C_CASTLE_UPDATE |  | CastleYieldMsg |
| 110 | 0x006E | U_C_PLAYER_EFFECT |  | PropertyUpdatedMsg |
| 111 | 0x006F | U_C_CHANNEL_ALERT |  | ChatChannelMsg |
| 112 | 0x0070 | U_C_QUEST_UPDAT |  | QuestUpdatedRspMsg |
| 113 | 0x0071 | U_C_HERO_INFO |  | SimpleHeroInfoMsg |
| 114 | 0x0072 | U_C_MAILITEM_MOVE_RESULT |  | MailPickupRspMsg |
| 115 | 0x0073 | U_C_BAG_MOVE_UPDATE |  | ItemMovedListMsg |
| 116 | 0x0074 | U_C_PAWN_INFO |  | ArmyPawnInfoMsg |
| 117 | 0x0075 | U_C_CONSORTIA_STATIC |  | ConsortiaMsg |
| 118 | 0x0076 | U_C_CASTLE_DEFENSE |  | CastleDefenseRspMsg |
| 120 | 0x0078 | U_C_CAMPAIGN_ROOM_MEMBER |  | RoomPlayerListMsg |
| 121 | 0x0079 | U_C_CAMPAIGN_ROOM_MASTER |  | ChangeMasterRspMsg |
| 123 | 0x007B | U_C_CAMPAIGN_LOGIN_OUT |  | CampaignLoginMsg |
| 124 | 0x007C | U_C_CAMPAIGN_LOGIN_IN |  | CampaignLoginMsg |
| 125 | 0x007D | U_C_CAMPAIGN_CREATE |  | RoomCreatedMsg |
| 126 | 0x007E | U_C_MSG |  | CampaignNotifyMsg |
| 127 | 0x007F | U_C_CAMPAIGN_NODE |  | CampaignNodeListMsg |
| 128 | 0x0080 | U_C_CAMPAIGN_NODE_UPDATE |  | CampaignNodeUpdateMsg |
| 129 | 0x0081 | U_C_NODE_SUCCESS |  | CampaignNodeSuccMsg |
| 130 | 0x0082 | U_C_CAMPAIGN_FOG |  | CampaignFogMsg |
| 131 | 0x0083 | U_C_CAMPAIGN_ARMY_UPDATE |  | ArmyArmyMsg |
| 132 | 0x0084 | U_C_CAMPAIGN_BOSS_ARMY_INVITE |  | BossInviteMsg |
| 133 | 0x0085 | U_C_CAMPAIGN_BOSS_ARMY_LIST |  | BossArmyListMsg |
| 134 | 0x0086 | U_C_CAMPAIGN_FINISH |  | (não lê corpo) |
| 135 | 0x0087 | U_C_CAMPAIGN_CARDS |  | CampaignCardsMsg |
| 137 | 0x0089 | U_C_CAMPAIGN_REPORT |  | CampaignReportMsg |
| 138 | 0x008A | U_C_GAME_PLOT |  | PlotMsg |
| 139 | 0x008B | U_C_ARMY_SUPPROT |  | (não lê corpo) |
| 140 | 0x008C | U_C_MAPDATA_SYNC |  | MapUpdatedMsg |
| 141 | 0x008D | U_C_LOCK_SCREEN |  | LockScreenRspMsg |
| 142 | 0x008E | U_C_CAMERA_MOVE |  | PlayerMoveCameraMsg |
| 143 | 0x008F | U_C_PLAY_MOVIE |  | PlayerMovieMsg |
| 145 | 0x0091 | U_C_WATERLOG_SEND |  | FarmLogRsp |
| 146 | 0x0092 | U_C_HARVEST_MSG |  | TreeUpdateRsp |
| 147 | 0x0093 | U_C_TREEINFO_UPDATE |  | TreeUpdateRsp |
| 148 | 0x0094 | U_C_NEW_MAIL |  | MailMsg |
| 149 | 0x0095 | U_C_HERO_BROAD_EQUIPMENT |  | HeroEquUpdatedMsg |
| 150 | 0x0096 | U_C_SERIAL_ARMY |  | ArmyArmyMsg |
| 151 | 0x0097 | U_C_BUILDING_ORDER_INFO |  | OrderInfoMsg |
| 152 | 0x0098 | U_C_SECURITY_INFO_UPDATE |  | CastleYieldMsg |
| 153 | 0x0099 | U_B_ATTACKING |  | AttackOrderMsg |
| 154 | 0x009A | U_B_PREPARE_OVER |  | PrepareOverMsg |
| 156 | 0x009C | U_B_START |  | BattleStartMsg |
| 157 | 0x009D | U_B_PREPARE |  | BattlePrepareMsg |
| 158 | 0x009E | U_B_USE_ITEM_RESULT |  | ItemUseResultMsg |
| 160 | 0x00A0 | U_CH_FRIEND_LOGIN |  | FriendRelationMsg |
| 161 | 0x00A1 | U_CH_FRIEND_LOGOUT |  | FriendRelationMsg |
| 162 | 0x00A2 | U_CH_CONSORTIA_USERLOGIN |  | ConsortiaMsg |
| 163 | 0x00A3 | U_CH_CONSORTIA_USERLOGOUT |  | ConsortiaMsg |
| 164 | 0x00A4 | U_CH_CONSORTIA_FRESHINFO |  | ConsortiaInfoMsg |
| 165 | 0x00A5 | U_CH_FRIEND_UPDATE |  | FriendInfoMsg |
| 169 | 0x00A9 | U_C_ARMY_UPDATE_GRID |  | OutercityArmyUpdatedGridMsg |
| 170 | 0x00AA | U_C_FAST_USE_BLOOD |  | FastUseBloodMsg |
| 187 | 0x00BB | U_C_ORE_MINE_RESP |  | OreMineRespMsg |
| 188 | 0x00BC | U_C_ORE_MINE_BASE_INFO |  | OreActiveBaseInfoMsg |
| 189 | 0x00BD | U_C_ORE_WINDOW_INFO |  | OreWindowMsg |
| 190 | 0x00BE | U_C_ORE_ACTIVE_OPEN_STATE |  | SimplePropertyMsg |
| 295 | 0x0127 | U_C_BOTTLE_DROP_DATA |  | BottleDropListMsg |
| 300 | 0x012C | U_C_GOLDENROAD_CLOSE |  | (não lê corpo) |
| 301 | 0x012D | U_C_FASHION_INFO |  | FashionInfoMsg |
| 337 | 0x0151 | U_C_MAIL_CHECK |  | MailCheckMsg |
| 338 | 0x0152 | U_C_GROUPON_DROPITEM |  | VipRouletteMsg |
| 345 | 0x0159 | U_C_CONSUM_RANK |  | ChargeRewardMsg |
| 357 | 0x0165 | U_C_MARRIAGE_DATA |  | MarriageDataMsg |
| 358 | 0x0166 | U_C_MARRIAGE_DEAL_DIVORCE |  | (não lê corpo) |
| 359 | 0x0167 | U_C_MARRIAGE_RECOMMENDLIST |  | RecommendListMsg |
| 363 | 0x016B | U_C_LUCK_EXCHANGE_TEMP_MSG |  | LuckExchangeTempListMsg |
| 364 | 0x016C | U_C_LUCK_EXCHANGE_DATA_MSG |  | LuckExchangeInfoListMsg |
| 365 | 0x016D | U_C_MATE_SKILL_SHOP |  | AltarShopListMsg |
| 414 | 0x019E | U_C_CHAIRS_OPENSTATE |  | SimplePropertyMsg |
| 415 | 0x019F | U_C_CHAIRS_INFO |  | ChairsListMsg |
| 513 | 0x0201 | U_C_SUPER_SIGNIN_CARD |  | SuperSigninCardRespMsg |
| 514 | 0x0202 | U_C_SUPER_SIGNIN_CARD_TEMP |  | SuperSigninRewardMsg |
| 3842 | 0x0F02 | U_G_LOGIN_OTHER |  | GatewayMsg |
| 4103 | 0x1007 | U_BATTLE_REPORT |  | BattleReportMsg |
| 4104 | 0x1008 | U_C_ARMY_POS_UPDATE |  | ArmyPosUpdatedMsg |
| 4105 | 0x1009 | U_C_NPC_CHASE_ARMY |  | NPCChaseMsg |
| 4122 | 0x101A | U_C_NPC_MOVE |  | NPCMoveMsg |
| 4124 | 0x101C | U_C_ESCORT_NPC_FOLLOW |  | NPCFollowMsg |
| 4125 | 0x101D | U_C_BAG_EQUIPLOOK |  | DetailRspMsg |
| 4126 | 0x101E | U_C_SEND_STANDPOS |  | StandPosMsg |
| 4128 | 0x1020 | U_C_SIMPLEUSER_INFO |  | InfoRspMsg |
| 4129 | 0x1021 | U_C_PHYSIC_LIST_UPDATE |  | PhysicListUpdateMsg |
| 4130 | 0x1022 | U_C_BUILDINGINFO_LIST |  | BuildingInfoListMsg |
| 4131 | 0x1023 | U_C_MAIL_LIST |  | ReceiveMailMsg |
| 4132 | 0x1024 | U_C_MAIL_DEL_RESULT |  | MailDelReqMsg |
| 4133 | 0x1025 | U_C_CONSORTIAUSER_LIST |  | SimplePlayerListRspMsg |
| 4134 | 0x1026 | U_C_CONSORTIA_OFFER_LIST |  | ConsortiaContributeRspMsg |
| 4135 | 0x1027 | U_C_INVITEINFO_LIST |  | ConsortiaUserInviteInfoListRspMsg |
| 4136 | 0x1028 | U_C_EVENT_LIST |  | ConsortiaEventListRspMsg |
| 4137 | 0x1029 | U_C_DUTY_LIST |  | ConsortiaDutyListRspMsg |
| 4138 | 0x102A | U_C_CONSORTIA_INFO |  | ConsortiaInfoMsg |
| 4139 | 0x102B | U_C_CONSORTIA_SEARCH |  | ConsortiaSearchRspMsg |
| 4140 | 0x102C | U_C_CONSORTIA_INVITE_LIST |  | SimplePlayerListRspMsg |
| 4141 | 0x102D | U_C_CONSORTIA_ALTERINFO |  | ConsortiaMsg |
| 4142 | 0x102E | U_C_CONSORTIA_ALTERITEM |  | ItemInfoMsg |
| 4143 | 0x102F | U_C_CONSORTIA_ADDFRESH |  | ConsortiaMsg |
| 4144 | 0x1030 | U_C_CONSORTIA_SITE |  | ConsortiaInfoMsg |
| 4145 | 0x1031 | U_C_SHOP_HASBUY |  | ShopMsg |
| 4146 | 0x1032 | U_C_TREE_FRIEND |  | FriendTreeRsp |
| 4148 | 0x1034 | U_C_CHECK_NICK |  | CheckNickMsg |
| 4149 | 0x1035 | U_B_LOAD_RES |  | ArmyResMsg |
| 4150 | 0x1036 | U_C_LEED_RECEIVE |  | LeedFinishedRspMsg |
| 4151 | 0x1037 | U_C_RANK_LIST |  | RankListRspMsg |
| 4152 | 0x1038 | U_C_LEED_UPDATE |  | LeedUpdatedRspMsg |
| 4153 | 0x1039 | U_C_LOAD_CASTLE |  | BaseCastleMsg |
| 4154 | 0x103A | U_C_LOAD_BUILD |  | BuildingInfoListMsg |
| 4155 | 0x103B | U_C_LOAD_BUILD_ORDER |  | BuildOrderList |
| 4156 | 0x103C | U_C_LOAD_FRIEND_LIST |  | FriendRelationList |
| 4157 | 0x103D | U_C_LOAD_WATER |  | LoadFarmRsp |
| 4158 | 0x103E | U_C_SEND_WATER_RESULT |  | FarmLogRsp |
| 4159 | 0x103F | U_C_TRASNBUILDING_RESULT |  | CastleReqMsg |
| 4160 | 0x1040 | U_C_SEND_SYSPROPERTY |  | SystemPropertyMsg |
| 4161 | 0x1041 | U_C_INVITE_PLAYER_LIST |  | RoomPlayerListMsg |
| 4162 | 0x1042 | U_C_PLAYER_MOVE |  | PlayerMoveMsg |
| 4163 | 0x1043 | U_C_NPC_CHAT |  | NPCChatMsg |
| 4164 | 0x1044 | U_C_ARMY_CHANGESHARP |  | ArmyChangeSharpMsg |
| 4165 | 0x1045 | U_C_BUFFER_LIST |  | CampaignBufferMsg |
| 4166 | 0x1046 | U_B_FIGHT_CANCELED |  | (não lê corpo) |
| 4167 | 0x1047 | U_C_BROAD_POS |  | PosMoveMsg |
| 4168 | 0x1048 | U_C_ARMY_REMOVE |  | ArmyRemoveMsg |
| 4169 | 0x1049 | U_C_CHALLENGE_INFO |  | ChallengeInfoMsg |
| 4170 | 0x104A | U_C_PLAYER_SEARCH |  | SimplePlayerSearchRspMsg |
| 4172 | 0x104C | U_C_PLAYER_AASCHANGE |  | PlayerAASRspMsg |
| 4173 | 0x104D | U_C_PLAYER_AASREFRESH |  | PlayerAASRefreshMsg |
| 4174 | 0x104E | U_C_SYNC_BOSS_HP |  | WorldBossInfoMsg |
| 4175 | 0x104F | U_C_PLAYER_DIE_STATE |  | PlayerStateListMsg |
| 4176 | 0x1050 | U_C_CHALLENGE_TIME |  | ChallengeCoolTimeMsg |
| 4177 | 0x1051 | U_C_PLAYER_SIGN |  | PlayerSignRspMsg |
| 4178 | 0x1052 | U_C_START_MOVE_UPDATE |  | StarMoveRspMsg |
| 4179 | 0x1053 | U_C_STAR_PICK |  | StarRandRspMsg |
| 4180 | 0x1054 | U_C_STAR_RAND |  | StarRandRspMsg |
| 4182 | 0x1056 | U_C_CAMPAIGN_STATE |  | WorldBossStateMsg |
| 4183 | 0x1057 | U_C_MULTI_HPSYNC |  | MultiCampaignHpSyncMsg |
| 4184 | 0x1058 | U_C_ITEM_SMITH |  | ItemSmithyMsg |
| 4185 | 0x1059 | U_C_ARMYPOS_BROAD |  | PosMoveMsg |
| 4186 | 0x105A | U_C_CAMPAIGN_ARMYPOS_SEND |  | ArmyFightPosEditListMsg |
| 4187 | 0x105B | U_C_BUILDING_ORDER_SEND |  | BuildOrderList |
| 4188 | 0x105C | U_C_ITEM_BUFFER |  | ItemBufferRspMsg |
| 4189 | 0x105D | U_C_PICK_HARVEST_MSG |  | TreeUpdateRsp |
| 4190 | 0x105E | U_C_CANWATER_USERS |  | LoadFarmRsp |
| 4192 | 0x1060 | U_C_SINGLEROOM_FAIL |  | (não lê corpo) |
| 4193 | 0x1061 | U_C_REFUSEFRIEND_REFRESH |  | RefuseFriendRspMsg |
| 4194 | 0x1062 | U_C_REFUSEINVITE_REFRESH |  | RefuseFriendRspMsg |
| 4195 | 0x1063 | U_C_OFFLINE_REWARD |  | OfflineRewardMsg |
| 4197 | 0x1065 | U_C_REWARD_FRESH |  | RewardFreshRspMsg |
| 4198 | 0x1066 | U_C_REWARD_UPDATE |  | RewardUpdatedRspMsg |
| 4199 | 0x1067 | U_C_LEFT_WEARY |  | HangupInfoMsg |
| 4200 | 0x1068 | U_C_HANGUP_STATE |  | HangupInfoMsg |
| 4201 | 0x1069 | U_C_MATCH_STATE |  | MatchStateMsg |
| 4202 | 0x106A | U_C_DATARESET |  | DataResetMsg |
| 4203 | 0x106B | U_C_WORLDBOSS_REPORT |  | WorldBossReportMsg |
| 4204 | 0x106C | U_C_HANGUP_ROOM_STATE |  | HangupStateListMsg |
| 4205 | 0x106D | U_C_TOWERINFO |  | TowerInfoMsg |
| 4206 | 0x106E | U_C_PLAYER_HANGUPSTATE |  | PlayerHangupStateListMsg |
| 4207 | 0x106F | U_C_TOWER_DIED |  | TowerDiedMsg |
| 4208 | 0x1070 | U_C_PLAYER_NODE_STATE |  | PlayerNodeStateMsg |
| 4224 | 0x1080 | U_C_LUCKY_REFRESH |  | PlayerLuckyMsg |
| 4227 | 0x1083 | U_CH_ADD_GROUP |  | FriendGroupMsg |
| 4228 | 0x1084 | U_CH_DEL_GROUP |  | FriendGroupMsg |
| 4229 | 0x1085 | U_CH_RENAME_GROUP |  | FriendGroupMsg |
| 4230 | 0x1086 | U_CH_FRIEND_MOVE |  | MoveFriendReqMsg |
| 4231 | 0x1087 | U_CH_PRIVATE_CHAT |  | ChatFriendMsg |
| 4232 | 0x1088 | U_CH_EXCHANGE_STATE |  | ChatStateMsg |
| 4233 | 0x1089 | U_C_SEND_VERSION |  | VersionMsg |
| 4234 | 0x108A | U_C_SYNCHRONIZED_TIME |  | SynchronizedTimeMsg |
| 4235 | 0x108B | U_C_HANGUP_SYNC |  | HangupInfoMsg |
| 4236 | 0x108C | U_CH_PRIVATE_CHAT_REPLY |  | ChatFriendMsg |
| 4237 | 0x108D | U_C_ARMY_POSATION |  | ArmyPositionMsg |
| 4238 | 0x108E | U_C_SHOP_MAIN |  | ShopMainRspMsg |
| 4239 | 0x108F | U_CH_SNS_UPDATED |  | SNSUpdatedMsg |
| 4240 | 0x1090 | U_C_ENTER_COPY_NUM_REFRESH |  | MultiCampaignEnterCountMsg |
| 4241 | 0x1091 | U_C_ARMYPOS_SEND |  | ArmyPositionMsg |
| 4242 | 0x1092 | U_C_GOLD_IMPOSERESULT |  | GoldImposeMsg |
| 4243 | 0x1093 | U_C_TAKECHALLENGE_RESULT |  | ChallengeRankRewardMsg |
| 4244 | 0x1094 | U_C_ISTAKE_CHALLENGEREWARD |  | ChallengeRankRewardMsg |
| 4245 | 0x1095 | U_CH_SNS_REQ |  | SNSInfoMsg |
| 4246 | 0x1096 | U_CH_FRIEND_ADDED |  | FriendAddedMsg |
| 4247 | 0x1097 | U_C_RATE_INFO |  | RateUpdateReqMsg |
| 4248 | 0x1098 | U_C_WARFIELD_STATE |  | WorldBossStateMsg |
| 4251 | 0x109B | U_C_ACTIVE |  | ActiveRspMsg |
| 4252 | 0x109C | U_C_WARFIELD_INFO |  | WarFightInfoMsg |
| 4253 | 0x109D | U_C_NODEPOS_REFERSH |  | CampaignNodePosRefershListMsg |
| 4254 | 0x109E | U_C_WARREPORT |  | WarReportListMsg |
| 4255 | 0x109F | U_C_ORDERREQUEST |  | WarReportListMsg |
| 4256 | 0x10A0 | U_CH_SIMPLEUSER_INFO |  | RelationPlayerMsg |
| 4258 | 0x10A2 | U_C_REFRESHFORRANDOM |  | SmithFreshRspMsg |
| 4260 | 0x10A4 | U_C_RESOLVE |  | (não lê corpo) |
| 4261 | 0x10A5 | U_C_STARSHOP_BUY |  | StarShopMsg |
| 4262 | 0x10A6 | U_C_BROADBUFFER |  | ArmyBufferListMsg |
| 4263 | 0x10A7 | U_C_ARMYPOS_FAIL |  | (não lê corpo) |
| 4264 | 0x10A8 | U_C_CAMPAIGN_NODE_ADD |  | CampaignNodeListMsg |
| 4265 | 0x10A9 | U_C_RELOADDIRTY |  | (não lê corpo) |
| 4266 | 0x10AA | U_C_CONSORTIA_PASS_USER |  | (não lê corpo) |
| 4267 | 0x10AB | U_C_CONSORTIA_LINK |  | ConsortiaLinkRspMsg |
| 4268 | 0x10AC | U_C_TAKEDROP_FAIL |  | BattleReportMsg |
| 4269 | 0x10AD | U_C_WARMOVIE |  | WarMovieMsg |
| 4270 | 0x10AE | U_C_ROOM_SEND |  | RoomMsg |
| 4271 | 0x10AF | U_C_PLAYER_RENAME_RSP |  | PlayerRenameRspMsg |
| 4272 | 0x10B0 | U_CH_CHAT_STATE |  | ChatStateListRspMsg |
| 4273 | 0x10B1 | U_CH_FRIEND_SEARCH |  | FriendSearchRspMsg |
| 4352 | 0x1100 | U_C_MALL_SELL_ITEM |  | SellItemRspMsg |
| 4353 | 0x1101 | U_C_MALL_LIST_SELL |  | AuctionItemsMsg |
| 4354 | 0x1102 | U_C_MALL_PLAYER_ITEMS |  | AuctionItemsMsg |
| 4355 | 0x1103 | U_C_MALL_AUCTION |  | AuctionItemRspMsg |
| 4356 | 0x1104 | U_C_MALL_LIST_AUCTION |  | AuctionItemsMsg |
| 4357 | 0x1105 | U_C_MALL_FIX_AUCTION |  | FixAuctionItemRspMsg |
| 4358 | 0x1106 | U_C_MALL_CANCEL_SELL |  | CanceltemRspMsg |
| 4359 | 0x1107 | U_C_MALL_SEARCH |  | AuctionItemsMsg |
| 4360 | 0x1108 | U_C_REWARD_COUNT |  | RewardCountUpdateRspMsg |
| 4361 | 0x1109 | U_B_BATTLE_NOTICE |  | BattleNoticeMsg |
| 4368 | 0x1110 | U_C_ITEM_REFRESHPROPERTY |  | RefreshPropertyRepMsg |
| 4369 | 0x1111 | C_WORLDBOSSWOUND_REWARD |  | WorldBossWoundRewardListMsg |
| 4370 | 0x1112 | U_C_ROOM_FIND_RESULT |  | RoomMsg |
| 4371 | 0x1113 | U_C_TIME_JUDGE |  | TimeJudgeMsg |
| 4372 | 0x1114 | U_C_REFININGSOUL_FRFRESH |  | PlayerRefiningSoulMsg |
| 4373 | 0x1115 | U_C_TOWERLIST |  | TowerListMsg |
| 4375 | 0x1117 | U_C_SHOP_DISCOUNT | a todos a cada compra de oferta (`currentCount` novo) | MainDiscountInfo |
| 4376 | 0x1118 | U_C_QUESTION_REPLAY |  | ReplayListMsg |
| 4377 | 0x1119 | U_C_REQUEST_GUILDCHALLENGE |  | GuildChallengeOrderListMsg |
| 4379 | 0x111B | U_C_REQUEST_GUILDLIST |  | GuildChallengeOrderListMsg |
| 4380 | 0x111C | U_C_SEND_NEEDOFFER |  | (não lê corpo) |
| 4381 | 0x111D | U_C_WORLDBOSS_LOAD |  | WorldBossInfoLoadMsg |
| 4382 | 0x111E | U_C_PLAY_GETMOIVE |  | FightOverMoiveMsg |
| 4383 | 0x111F | U_C_SHOPITEM_BUY |  | ShopItemBuyRspMsg |
| 4384 | 0x1120 | U_C_SHOPITEM_FRESH |  | ShopFreshRspMsg |
| 4386 | 0x1122 | U_C_FARM_INFO |  | FarmInfoRspMsg |
| 4387 | 0x1123 | U_C_FARMLAND_INFO |  | FarmInfoRspMsg |
| 4388 | 0x1124 | U_C_SNSINFO |  | SnsRspMsg |
| 4389 | 0x1125 | U_C_CONSORTIA_VOTING_LIST |  | ConsortiaVotingUsersMsg |
| 4390 | 0x1126 | U_C_CONSORTIA_VOTING |  | ConsortiaVotingRspMsg |
| 4391 | 0x1127 | U_C_BLESS_REFRESH |  | BlessingMsg |
| 4392 | 0x1128 | U_C_OPEN_CUSTOMER |  | FastOpenCustomerMsg |
| 4393 | 0x1129 | U_C_DAYACTION |  | DayActiveRspMsg |
| 4402 | 0x1132 | U_C_SECURITY_CODE |  | CheckImageMsg |
| 4410 | 0x113A | U_C_VIP_INFO |  | VipInfoMsg |
| 4412 | 0x113C | U_C_CLICKDATA |  | ClickDatasRspMsg |
| 4414 | 0x113E | U_C_OPENVIPROULETTE |  | VipRouletteMsg |
| 4415 | 0x113F | U_C_VIPROULETTE_RESULT |  | VipRouletteMsg |
| 4416 | 0x1140 | U_C_VIP_OPENTIPS |  | (não lê corpo) |
| 4419 | 0x1143 | U_C_TOWER_REPORT |  | TowerInfoMsg |
| 4420 | 0x1144 | U_C_CHECK_SEND |  | CheckSend |
| 4421 | 0x1145 | U_C_HANGUP_PVP |  | HangupAttackMsg |
| 4422 | 0x1146 | U_C_SWITCH |  | SwitchInfoListMsg |
| 4423 | 0x1147 | U_C_REPLACEMENT_STATE |  | ReplacementMsg |
| 4424 | 0x1148 | U_C_OPRATE_REPLACEMENT_STATE |  | OprateReplacemntMsg |
| 4425 | 0x1149 | U_C_CAMPAIGN_SWEEP |  | CampaignSweepRsp |
| 4426 | 0x114A | U_C_MOUNT_UPDATE |  | MountInfoMsg |
| 4427 | 0x114B | U_C_MOUNT_AVATARLIST |  | MountAvatarMsg |
| 4428 | 0x114C | U_C_QUESTIONNARIE_LIST |  | QuestionnarieInfoMsg |
| 4429 | 0x114D | U_C_QUESTIONNARIE_ANSWER |  | QuestionDataRspMsg |
| 4430 | 0x114E | U_C_TALENT_GRADE_UP |  | TalentUpGradeMsg |
| 4431 | 0x114F | U_C_TALENT_INFO |  | HeroTalentMsg |
| 4432 | 0x1150 | U_C_FAM_TREE |  | FamInfoMsg |
| 4434 | 0x1152 | U_C_KING_CONTRACTE |  | KingContractMsg |
| 4435 | 0x1153 | U_C_ADD_BOSS_HP |  | BossHpMsg |
| 4436 | 0x1154 | U_C_OPEN_CONSORTIA__ALTAR |  | ConsortiaAltarOpenRspMsg |
| 4437 | 0x1155 | U_C_CONSORTIA_ALTAR_REPORT |  | AltarCampaignReportMsg |
| 4438 | 0x1156 | U_C_WORLD_PROSPERITY |  | SimplePropertyMsg |
| 4439 | 0x1157 | U_C_GUILDWAR_SCORE |  | GuildWarInfoListMsg |
| 4440 | 0x1158 | U_C_GUILDWAR_BUFFER |  | GuildBufferListMsg |
| 4441 | 0x1159 | U_C_GUILDWAR_TEAM |  | GuildGroupListMsg |
| 4448 | 0x1160 | U_C_ALTARNPC_MOVE |  | CampaignNpcMoveListMsg |
| 4449 | 0x1161 | U_C_ALTAROVER_MSG |  | SimplePropertyMsg |
| 4450 | 0x1162 | U_C_NODE_HP |  | NodeHpListMsg |
| 4451 | 0x1163 | U_C_GUILDWAR_STATE |  | GuildMsg |
| 4452 | 0x1164 | U_C_CASTLE_TIME |  | BaseCastleMsg |
| 4453 | 0x1165 | U_C_FAM_INFO |  | FamInfoMsg |
| 4455 | 0x1167 | U_C_CONSORTIA_VIP |  | VipToConsortiaMsg |
| 4456 | 0x1168 | U_C_CAMPIAGN_OPEN_MV |  | (não lê corpo) |
| 4457 | 0x1169 | U_C_GUILDWAR_OPEN_LEFTTIME |  | GuildMsg |
| 4458 | 0x116A | U_C_GUILDLAST_WEEK_ORDER |  | GuildGroupListMsg |
| 4459 | 0x116B | U_C_MOUNT_INFO_SEND |  | MountInfoMsg |
| 4460 | 0x116C | U_C_GUILDWAR_WOUND |  | WorldBossInfoMsg |
| 4461 | 0x116D | U_C_REBATE_ACTIVE |  | RebateInfoMsg |
| 4462 | 0x116E | U_C_GUILDWAR_JOIN_PLAYER_COUNT |  | GuildJoinPlayerInfoMsg |
| 4463 | 0x116F | U_C_REBATE_DATA |  | UserRebateMsg |
| 4464 | 0x1170 | U_C_CROSS_USER_INFO |  | SimpleHeroInfoMsg |
| 4465 | 0x1171 | U_C_CONSORTIA_TREASURE_BOX |  | ConsortiaTreasureBoxMsg |
| 4466 | 0x1172 | U_C_CONSORTIA_BOX_INFO |  | ConsortiaStorageInfoMsg |
| 4467 | 0x1173 | U_BUY_TRIAL_RESULT |  | TrialInfoMsg |
| 4468 | 0x1174 | U_HERO_TRIAL_IFNO |  | PlayerTrialMsg |
| 4470 | 0x1176 | U_C_MYSTERYEVENT_LIST |  | MysteryEventListMsg |
| 4471 | 0x1177 | U_C_DAYGESTE_SEND |  | SimplePropertyMsg |
| 4474 | 0x117A | U_C_VEHICLE_NPC_NODE |  | VehicleNpcNodeListMsg |
| 4475 | 0x117B | U_C_SUM_ACTIVE_TEMP |  | SumActivesMsg |
| 4476 | 0x117C | U_C_SUMACTIVE_DATA |  | SumActiveDataMsg |
| 4479 | 0x117F | U_C_STAR_COMPOSE |  | StarRandRspMsg |
| 4481 | 0x1181 | U_C_ISTAKE_CROSS_SCORE_REWARD |  | ChallengeRankRewardMsg |
| 4482 | 0x1182 | U_C_CROSS_SCORE_REWARD_RESULT |  | ChallengeRankRewardMsg |
| 4483 | 0x1183 | U_WARFIELD_FORCE_QUIT |  | (não lê corpo) |
| 4484 | 0x1184 | U_APPELL_DATA |  | AppellsMsg |
| 4485 | 0x1185 | U_CONSORTIA_ALTAR_USE_SKILL |  | AltarCampaignSkillMsg |
| 4486 | 0x1186 | U_C_FASHION_SHOP_BUY |  | FashionShopMsg |
| 4487 | 0x1187 | U_C_FASHION_COMPOSE |  | StoreRspMsg |
| 4490 | 0x118A | U_CCC |  | SimplePropertyMsg |
| 4491 | 0x118B | U_APPELL_GET |  | (não lê corpo) |
| 4492 | 0x118C | U_C_GAMETIMES_INFO |  | (não lê corpo) |
| 4493 | 0x118D | U_CHECK_WARFIELD_COUNT_RS |  | CampaignReqMsg |
| 4494 | 0x118E | U_C_CROSS_ARMY_UPDATE |  | CrossArmyListMsg |
| 4495 | 0x118F | U_C_RUNE_OP |  | HeroRuneOpMsg |
| 4497 | 0x1191 | U_C_BOTTLE_PASS |  | BottlePassMsg |
| 4500 | 0x1194 | U_C_SMALL_BUGLE_FREE_COUNT |  | CampaignReqMsg |
| 4501 | 0x1195 | U_C_VEHICLE_TECH_RSP |  | SimplePropertyMsg |
| 4512 | 0x11A0 | U_C_VEHICLE_STATE |  | MatchStateMsg |
| 4513 | 0x11A1 | U_C_VEHICLE_JOIN |  | PlayerVehicleListMsg |
| 4514 | 0x11A2 | U_C_VEHICLE_END |  | VehicleCampaignDetailMsg |
| 4515 | 0x11A3 | U_C_VEHICLE_PROFILE_CHANGE |  | PlayerVehicleProfileMsg |
| 4516 | 0x11A4 | U_C_VEHICLE_LIST_RSP |  | PlayerVehicleListMsg |
| 4517 | 0x11A5 | U_C_VEHICLE_CAMPAIGN_LIST_RSP |  | PlayerVehicleListMsg |
| 4518 | 0x11A6 | U_C_VEHICLE_DETAILE |  | VehicleCampaignDetailMsg |
| 4519 | 0x11A7 | U_C_VEHICLE_MOVE |  | VehicleMoveMsg |
| 4520 | 0x11A8 | U_C_VEHICLE_ATTACK_RSP |  | VehicleAttackRspMsg |
| 4521 | 0x11A9 | U_C_VEHICLE_SYNC_SKILL |  | VehicleSkillListMsg |
| 4522 | 0x11AA | U_C_VEHICLE_SYNC_BUFF |  | VehicleBuffListMsg |
| 4523 | 0x11AB | U_C_VEHICLE_EXIT |  | VehicleExitMsg |
| 4524 | 0x11AC | U_C_VEHICLE_BOSS_ATTACK_TIP |  | VehicleAttackRspMsg |
| 4525 | 0x11AD | U_C_VEHICLE_ROOM_START_COUNT |  | SimplePropertyMsg |
| 4526 | 0x11AE | U_C_BOTTLE_RESULT |  | BottleScoreMsg |
| 4527 | 0x11AF | U_C_RUNE_RESET |  | (não lê corpo) |
| 4529 | 0x11B1 | U_C_LORDS_LOAD_MAINBORAD |  | LordsOrderListMsg |
| 4530 | 0x11B2 | U_C_LORDS_ENTER_RESULT |  | LordsOrderListMsg |
| 4531 | 0x11B3 | U_C_LORDS_FINAL_ORDERLIST |  | LordsOrderListMsg |
| 4532 | 0x11B4 | U_C_REQUEST_BET_LIST |  | LordsOrderListMsg |
| 4533 | 0x11B5 | U_C_SEND_FINALRWARD_STATE |  | (não lê corpo) |
| 4534 | 0x11B6 | U_C_TAKEFINALREWARD_RESULT |  | SimplePropertyMsg |
| 4535 | 0x11B7 | U_C_LORDS_OPENSTATE |  | SimplePropertyMsg |
| 4536 | 0x11B8 | U_C_LORDS_CLOSE |  | (não lê corpo) |
| 4537 | 0x11B9 | U_C_LORDS_LOCAL_FIANL_ORDER |  | LordsOrderListMsg |
| 4538 | 0x11BA | U_C_LORDS_FINAL_TIPS |  | PropertyMsg (param4) |
| 4539 | 0x11BB | U_C_VIP_FIRST |  | (não lê corpo) |
| 4540 | 0x11BC | U_C_PLAYER_PETINFO |  | PlayerPetMsg |
| 4541 | 0x11BD | U_C_CROSS_BIGBUGLE |  | CrossBigBugleMsg |
| 4542 | 0x11BE | U_C_FASHION_BOOK |  | FashionMsg |
| 4543 | 0x11BF | U_C_REQUEST_360_REWARD |  | PrivilegeMsg |
| 4544 | 0x11C0 | U_C_FATE_REQUEST |  | FateListMsg |
| 4545 | 0x11C1 | U_C_FATE_TURNREQUEST |  | FateEditMsg |
| 4546 | 0x11C2 | U_C_GAME_STORY_DROP |  | (não lê corpo) |
| 4547 | 0x11C3 | U_C_FLASHSALE_FRESH |  | ShopMsg |
| 4548 | 0x11C4 | U_C_SYNC_MINE_TRAMCAR |  | TramcarInfoMsg |
| 4549 | 0x11C5 | U_C_MINE_ACTIVE_STATE |  | GuildMsg |
| 4550 | 0x11C6 | U_C_NEW_PLAYER_GIFT |  | (não lê corpo) |
| 4551 | 0x11C7 | U_C_UPDATE_AREA |  | (não lê corpo) |
| 4552 | 0x11C8 | U_C_RES_SINGLEPASS_INFO |  | SinglePassMsg |
| 4553 | 0x11C9 | U_C_BUGLE_REQ |  | VipRouletteMsg |
| 4554 | 0x11CA | U_C_BUGLE_REWARDS |  | VipRouletteMsg |
| 4555 | 0x11CB | U_C_DRAGON_REQ |  | FateListMsg |
| 4556 | 0x11CC | U_C_TRANSFER |  | SimplePropertyMsg |
| 4557 | 0x11CD | U_C_TRANS_GRADE |  | FateInfoMsg |
| 4558 | 0x11CE | U_C_MOULD_ITEM |  | StoreRspMsg |
| 4559 | 0x11CF | U_C_GROUPON_INFO |  | GrouponShopMsg |
| 4560 | 0x11D0 | U_C_GROUPON_RESULT |  | GrouponShopMsg |
| 4590 | 0x11EE | U_C_TOP_TOOL_BTN |  | SimplePropertyMsg |
| 4592 | 0x11F0 | U_C_PLAYER_SPACE_ENTER |  | RoomEnterMsg |
| 4593 | 0x11F1 | U_C_PLAYER_SPACE_LEAVE |  | CampaignExitMsg |
| 4594 | 0x11F2 | U_C_PLAYER_SPACE_SYNC_POS |  | SpacePlayerMoveMsg |
| 4595 | 0x11F3 | U_C_PLAYER_SPACE_CREATE |  | RoomEnterMsg |
| 4597 | 0x11F5 | U_C_PLAYER_SPACE_SEND_EXSIT |  | RoomEnterMsg |
| 4598 | 0x11F6 | U_C_PLAYER_LOGIN_SYNC_MAPID |  | SimplePropertyMsg |
| 4599 | 0x11F7 | U_C_BUY_DISCOUNT |  | ShopMsg |
| 4600 | 0x11F8 | U_C_UPDATE_AWAKE |  | AwakeMsg |
| 4601 | 0x11F9 | U_C_PLAYER_SPACE_EVENT |  | SimplePropertyMsg |
| 4606 | 0x11FE | U_C_PLAYER_RETURN_TO_SPACE |  | RoomEnterMsg |
| 4607 | 0x11FF | U_C_PLAYER_REMOVE_IN_SPACE |  | SpacePlayerMoveMsg |
| 4608 | 0x1200 | U_C_RECEIVE_PET_DATA |  | PlayerPetMsg |
| 4609 | 0x1201 | U_C_NPC_LOCK |  | NodeLockReqMsg |
| 4610 | 0x1202 | U_C_VIPMOUNT_STATE |  | SimplePropertyMsg |
| 4611 | 0x1203 | U_C_PET_CHALLENGE_LIST |  | PetChallengeInfoMsg |
| 4612 | 0x1204 | U_C_ACTIVE_DEPOSIT |  | DepositActiveMsg |
| 4613 | 0x1205 | U_C_PET_RANK_REWARD |  | RankRewardMsg |
| 4614 | 0x1206 | U_C_REPEAT_REWARD_UPDATE |  | RewardUpdatedRspMsg |
| 4615 | 0x1207 | U_C_REPEAT_REWARD_END |  | (não lê corpo) |
| 4616 | 0x1208 | U_C_REPEAT_REWARD_FNISHED_SUM_UPDATE |  | SimplePropertyMsg |
| 4617 | 0x1209 | U_C_REPEAT_REWARD_FINISH |  | (não lê corpo; vazio no fim de cada anel, offer._ring_done) |
| 4618 | 0x120A | U_C_PLAYER_ADDITION |  | AdditionMsg |
| 4619 | 0x120B | U_C_TOP_CHALLENGE_INFO |  | PetChallengeInfoMsg |
| 4620 | 0x120C | U_C_TEAM_INVITE |  | InviteTeamMsg |
| 4621 | 0x120D | U_C_TEAM_LEAVE_FOR_NOW |  | SimplePropertyMsg |
| 4622 | 0x120E | U_C_TEAM_CREATE |  | TeamInfoMsg |
| 4624 | 0x1210 | U_C_TEAM_PLAYER_INFO |  | TeamInfoMsg |
| 4625 | 0x1211 | U_C_TEAM_DISMISS |  | (não lê corpo) |
| 4626 | 0x1212 | U_C_TEAM_ADD_MEMBER |  | TeamInfoMsg |
| 4627 | 0x1213 | U_C_TEAM_CAPTAIN_CHANGE |  | SimplePropertyMsg |
| 4628 | 0x1214 | U_C_TEAM_FIGHT_POS_CHANGE |  | MemberFightPosListMsg |
| 4629 | 0x1215 | U_C_TEAM_MEMBER_LEFT |  | SimplePropertyMsg |
| 4630 | 0x1216 | U_C_TEAM_KICK_MEMBER |  | SimplePropertyMsg |
| 4631 | 0x1217 | U_C_BATTLEGUARD_INFO |  | HeroWatchMsg |
| 4632 | 0x1218 | U_C_SENDFAMLORDS_INFO |  | FamLordsInfoMsg |
| 4633 | 0x1219 | U_C_TREASUREMAP_INFO |  | PlayerTreasureMsg |
| 4634 | 0x121A | U_C_TREASUREMAP_REWARD |  | (não lê corpo) |
| 4635 | 0x121B | U_C_REFUSETEAMINVITE_REFRESH |  | RefuseFriendRspMsg |
| 4636 | 0x121C | U_C_LOTTERY |  | LotteryMsg |
| 4637 | 0x121D | U_C_LOTTERY_STATE |  | LotteryMsg |
| 4638 | 0x121E | U_C_SERVEN_LEAD |  | ServenDayLeadMsg |
| 4639 | 0x121F | U_C_LOTTERY_NOTICE |  | LotteryMsg |
| 4640 | 0x1220 | U_C_FRESHMAN_DEPOSIT |  | DepositActiveMsg |
| 4641 | 0x1221 | U_C_LOTTERY_ITEMS |  | VipRouletteMsg |
| 4642 | 0x1222 | U_C_LOTTERY_RESULT |  | SimplePropertyMsg |
| 4643 | 0x1223 | U_C_TOLLGAGEINFO |  | TollgateMsg |
| 4644 | 0x1224 | U_C_TOLLGAGE_GETREWARD |  | (não lê corpo) |
| 4645 | 0x1225 | U_C_TOLLGATE_IS_OPEN |  | TollgateMsg |
| 4646 | 0x1226 | U_C_TOLLGATE_SCORE |  | TollgateMsg |
| 4647 | 0x1227 | U_C_TOLLGATE_REWARD |  | TollgateRewardMsg |
| 4648 | 0x1228 | U_C_VIPCUSTOM_NOTIFY |  | SimplePropertyMsg |
| 4656 | 0x1230 | U_C_ENGAGE_LIST |  | EngageMsg |
| 4657 | 0x1231 | U_C_MARRIAGE_INFO |  | MarriageMsg |
| 4658 | 0x1232 | U_C_SPECIFICATION_INFO |  | MarriageProMsg |
| 4659 | 0x1233 | U_C_ENGAGED_INFO |  | MarriageProMsg |
| 4660 | 0x1234 | U_C_MARRIAGE_CAMPAING_OATH |  | MarriageProMsg |
| 4662 | 0x1236 | U_C_MARRIAGE_CAMPAING_LIST |  | EngageMsg |
| 4672 | 0x1240 | U_C_MARRIAGE_RIDE |  | MarriageProMsg |
| 4673 | 0x1241 | U_C_MARRIAGE_CAMPAING_INFO |  | EngageMsg |
| 4674 | 0x1242 | U_C_MARRIAGE_CAMPAING |  | MarriageProMsg |
| 4675 | 0x1243 | U_C_MARRIAGE_TASK_UPDATE |  | RewardUpdatedRspMsg |
| 4676 | 0x1244 | U_C_MARRIAGE_CAMPAIGN_MOVE |  | MarriageProMsg |
| 4678 | 0x1246 | U_C_MARRIAGE_TREE |  | MarriageTreeMsg |
| 4679 | 0x1247 | U_C_MOUNT_UPGRADESTAR |  | AvatarInfoMsg |
| 4681 | 0x1249 | U_C_CROSSGUILD_GROUP_SEND |  | CrossGuildMsg |
| 4682 | 0x124A | U_C_CROSSGUILD_GROUP_OWNER |  | CrossGuildMsg |
| 4683 | 0x124B | U_C_CROSSGUILD_STATE |  | GuildMsg |
| 4685 | 0x124D | U_C_CROSSGUILD_FIRST |  | GuildInfoMsg |
| 4686 | 0x124E | U_C_PETISLAND_BOSS_START |  | PetIslandDefendStateMsg |
| 4690 | 0x1252 | U_C_MARRIAGE_HEART_START |  | (não lê corpo) |
| 4691 | 0x1253 | U_C_MARRIAGE_HEART_QUESTION |  | MarriageHeartMsg |
| 4696 | 0x1258 | U_C_VICEPASSWORD |  | VicePasswordMsg |
| 4709 | 0x1265 | U_C_RENTAL_BAG |  | RentalBagOpResMsg |
| 4725 | 0x1275 | U_C_PLAYER_TOKENINFO |  | PlayerTokenInfoMsg |
| 4741 | 0x1285 | U_C_CROSSGUILD_ICON |  | SimplePropertyMsg |
| 4745 | 0x1289 | U_C_CHARGE_RANK |  | ChargeRewardMsg |
| 4758 | 0x1296 | U_C_QUERY_CHILD |  | PlayerChildInfoMsg |
| 4776 | 0x12A8 | U_C_PVP_TIMER |  | TimerInfoListMsg |
| 4798 | 0x12BE | U_C_MATE_LORDS_INFO |  | MateLordsListMsg |
| 4799 | 0x12BF | U_C_MATE_LORDS_MAININFO |  | MateLordsListMsg |
| 4801 | 0x12C1 | U_C_MATE_LORDS_OPENSTATE |  | SimplePropertyMsg |
| 4803 | 0x12C3 | U_CROSS_BATTLE_VIEW |  | SimplePropertyMsg |
| 4804 | 0x12C4 | U_CROSS_VIEW_BATTLE_INFO |  | SimplePropertyMsg |
| 4806 | 0x12C6 | U_C_MULTI_LORDS_FIANL_ORDER |  | (não lê corpo) |
| 4811 | 0x12CB | U_C_SELECT_NEW_YEAR_BOX_NODE |  | QueryCollectCampaignNodeRspMsg |
| 4825 | 0x12D9 | U_C_BOTTLE_ACTIVE |  | BottleMsg |
| 4900 | 0x1324 | U_C_KING_INFO |  | KingTowerInfoMsg |
| 4901 | 0x1325 | U_C_SLOTINFO |  | SlotActiveMsg |
| 4902 | 0x1326 | U_C_POWCARD_Fight_ADD |  | PowcardFightAddMsg |
| 4903 | 0x1327 | U_C_POWCARD_BUF_ON |  | PowCardBufListMsg |
| 4905 | 0x1329 | U_C_POWCARD_ALL |  | PowCardSuiteListMsg |
| 4906 | 0x132A | U_C_FBEVENT |  | FbEventMsg |
| 4907 | 0x132B | U_C_ANSWER_PLAYER_INFO |  | playeranswerquestionMsg |
| 4908 | 0x132C | U_C_ANSWER_SYSTEM_STATE |  | SysAnswerQuestionStateMsg |
| 4909 | 0x132D | U_C_ANSWER_SINGLER_QUESTION |  | singleranswerquestionMsg |
| 4910 | 0x132E | U_C_ANSWER_RANK_LIST |  | TenAnswerQuestionOrderMsg |
| 4911 | 0x132F | U_C_ACTIVE_CODE |  | UseConvertCodeMsg |
| 4912 | 0x1330 | U_C_RECOVER |  | RecoverInfosMsg |
| 4913 | 0x1331 | U_C_MULITY_CAMPAIGN_REQUEST |  | SimplePropertyMsg |
| 4914 | 0x1332 | U_C_SEEK_LOADNODEINFO |  | PlayerSeekInfoMsg |
| 4915 | 0x1333 | U_C_SEEK_MESSAGE |  | MessageForSeekMsg |
| 4916 | 0x1334 | U_C_FISH_POOL |  | FishPoolMsg |
| 4917 | 0x1335 | U_C_FISH_CHECK |  | FishResultMsg |
| 4918 | 0x1336 | U_C_FISH_INFOS |  | FishInfosMsg |
| 4919 | 0x1337 | U_C_FISH_HELPOVER |  | HelpOverMsg |
| 4920 | 0x1338 | U_C_FISH_CRAZY |  | CrazyFishInfoMsg |
| 4921 | 0x1339 | U_C_FBEVENT2 |  | FbShareMsg |
| 4922 | 0x133A | U_C_GEMMAZE_INFO |  | GemMazeInfoMsg |
| 4923 | 0x133B | U_C_GEMMAZE_UPDATE |  | GemInfoUpdateMsg |
| 4924 | 0x133C | U_GEMMAZE_OPRST |  | GemInviteOpMsg |
| 4925 | 0x133D | U_GEMMAZE_INVIDE_NOTICE |  | GemMoveInviteReqMsg |
| 4927 | 0x133F | U_GEMMAZE_BUYTIMES_RSP |  | (não lê corpo) |
| 4928 | 0x1340 | U_GEMMAZE_GETBOX_RSP |  | GetRewardBoxRspMsg |
| 4933 | 0x1345 | U_C_GOLDENROAD_FRESH |  | GoldenRoadMsg |
| 4934 | 0x1346 | U_C_GOLDENROAD_CASTDICE |  | CastDiceMsg |
| 4936 | 0x1348 | U_C_LEAD_EXTRACT |  | LeadRewardMsg |
| 4938 | 0x134A | U_C_MAPBOSS_DATAS |  | MapBossMsg |
| 4939 | 0x134B | U_C_MAPBOSS_FOG |  | MapBossMsg |
| 4940 | 0x134C | U_C_MAPBOSS_BOX |  | MapBoxMsg |
| 4980 | 0x1374 | U_C_ICON_NUM |  | IconNumMsgList |
| 5004 | 0x138C | U_C_USER_DISPLAY | OutercityReqMsg |  |
| 5005 | 0x138D | U_C_BAG_MOVE | ItemReqMsg |  |
| 5006 | 0x138E | U_C_BAG_USEITEM | ItemUseMsg |  |
| 5007 | 0x138F | U_C_BAG_SELL | ItemReqMsg |  |
| 5008 | 0x1390 | C_HERO_UPDATE_EQUIPMENT, U_C_HERO_UPDATE_EQUIPMENT | HeroHideFashionReqMsg |  |
| 5010 | 0x1392 | U_C_BAG_BUY | PayTypeMsg |  |
| 5011 | 0x1393 | C_BAG_USEBIGBUGLE | ChatChannelMsg |  |
| 5012 | 0x1394 | U_C_QUEST_ADD | QuestAddedMsg |  |
| 5014 | 0x1396 | U_C_QUEST_FINISH | QuestFinishedReqMsg |  |
| 5015 | 0x1397 | U_C_CASTLE_UPDATE | (sem corpo) |  |
| 5017 | 0x1399 | U_C_PLAYER_NOVICE | NoviceReqMsgMsg |  |
| 5018 | 0x139A | U_C_PLAYER_GRADE | BoxBoxMsg |  |
| 5019 | 0x139B | U_C_PLAYER_TIME | BoxBoxMsg |  |
| 5020 | 0x139C | U_C_PLAYER_LOGINSTATE | (sem corpo) |  |
| 5021 | 0x139D | U_C_PLAYER_ADD_ATTACKCOUNT | PlayerChallengeMsg |  |
| 5022 | 0x139E | U_C_MAILITEM_MOVE | MailMsg |  |
| 5023 | 0x139F | U_C_CAMPAIGN_ROOM_CREATE | RoomReqMsg |  |
| 5024 | 0x13A0 | U_C_CAMPAIGN_ROOM_ENTER | RoomReqMsg |  |
| 5025 | 0x13A1 | U_C_CAMPAIGN_ROOM_EXIT | RoomExitMsg |  |
| 5026 | 0x13A2 | U_C_CAMPAIGN_ROOM_LIST | RoomReqMsg |  |
| 5027 | 0x13A3 | U_C_CAMPAIGN_INVITE_PLAYER_LIST | (sem corpo) |  |
| 5028 | 0x13A4 | U_C_CAMPAIGN_ROOM_INVITE | RoomReqMsg |  |
| 5029 | 0x13A5 | U_C_CAMPAGIN_ROOM_PLACESTATE | RoomReqMsg |  |
| 5030 | 0x13A6 | U_C_CAMPAIGN_ROOM_MASTER_CHANGE | CampaignReqMsg |  |
| 5031 | 0x13A7 | U_C_CAMPAIGN_ROOM_KILLPLAYER | RoomReqMsg |  |
| 5032 | 0x13A8 | U_C_CAMPAIGN_CALLBACK | CallBackReqMsg |  |
| 5033 | 0x13A9 | U_C_CAMPAIGN_CONFIRM | CampaignReqMsg |  |
| 5034 | 0x13AA | U_C_CAMPAIGN_ROOM_EDIT | RoomReqMsg |  |
| 5035 | 0x13AB | U_PLAYER_CLIENT_STATE | LoginStateMsg |  |
| 5036 | 0x13AC | U_C_PLAYER_READY_STATE | RoomReqMsg |  |
| 5037 | 0x13AD | U_C_ROOM_STATE | RoomReqMsg |  |
| 5038 | 0x13AE | U_C_CAMPAIGN_SYSTEM_ARMY | CampaignReqMsg |  |
| 5039 | 0x13AF | U_C_CAMPAIGN_ENTER | CampaignReqMsg |  |
| 5041 | 0x13B1 | C_MICRO_CLIENT_INFO | SimplePropertyMsg |  |
| 5120 | 0x1400 | U_C_CAMPAIGN_EXIT | RoomExitMsg |  |
| 5121 | 0x1401 | U_C_CAMPAIGN_ARMY | CampaignReqMsg |  |
| 5122 | 0x1402 | U_C_CAMPAIGN_TAKE_CARD | CampaignReqMsg |  |
| 5124 | 0x1404 | U_C_CAMPAIGN_SYNCPOS | PosMoveMsg |  |
| 5125 | 0x1405 | U_C_CAMPAIGN_ARRIVE | CampaignReqMsg |  |
| 5126 | 0x1406 | U_C_CAMPAIGN_FOG_UPDATE | CampaignFogDataListReqMsg |  |
| 5127 | 0x1407 | U_C_CAMPAIGN_TRAINING | NoviceReqMsgMsg |  |
| 5129 | 0x1409 | U_C_DROPITEM_TAKE | CampaignReqMsg |  |
| 5130 | 0x140A | U_C_CONSORTIA_CREATE | ConsortiaMsg |  |
| 5131 | 0x140B | U_C_CONSORTIA_CHANGE | ConsortiaMsg |  |
| 5132 | 0x140C | U_C_CONSORTIA_DELUSER | ConsortiaMsg |  |
| 5133 | 0x140D | U_C_CONSORTIA_LEVEL | ConsortiaMsg |  |
| 5134 | 0x140E | U_C_CONSORTIA_PASS | ConsortiaMsg |  |
| 5135 | 0x140F | U_C_CONSORTIA_USERINVITE | ConsortiaMsg |  |
| 5137 | 0x1411 | U_C_CONSORTIA_DUTYUPDATE | ConsortiaMsg |  |
| 5139 | 0x1413 | U_C_CONSORTIA_MODIFYBBS | ConsortiaMsg |  |
| 5140 | 0x1414 | U_C_CONSORTIA_MODIFYDESC | ConsortiaMsg |  |
| 5141 | 0x1415 | U_C_CONSORTIA_INVITEDEL | ConsortiaMsg |  |
| 5142 | 0x1416 | U_C_CONSORTIA_INVITE | ConsortiaMsg |  |
| 5143 | 0x1417 | U_C_CONSORTIA_USERPASS | ConsortiaMsg |  |
| 5144 | 0x1418 | U_C_CONSORTIA_OFF | ConsortiaUserOfferReqMsg |  |
| 5145 | 0x1419 | U_C_CONSORTIA_FRESHALTAR | SimplePropertyMsg |  |
| 5146 | 0x141A | U_C_CONSORTIA_QUIT | ConsortiaQuitReqMsg |  |
| 5147 | 0x141B | U_C_CONSORTIA_LEARN | ConsortiaMsg |  |
| 5148 | 0x141C | U_C_CONSORTIA_RENAME | ConsortiaRenameReqMsg |  |
| 5149 | 0x141D | U_C_CONSORTIA_OPENAPP | ConsortiaMsg |  |
| 5150 | 0x141E | U_C_ITEM_STRENGTHEN | (sem corpo) |  |
| 5151 | 0x141F | U_C_ITEM_INLAY | StoreReqMsg |  |
| 5152 | 0x1420 | U_C_ITEM_INLAYJOIN | StoreReqMsg |  |
| 5153 | 0x1421 | U_C_ITEM_COMPOSE | StoreReqMsg |  |
| 5154 | 0x1422 | U_C_SHOP_BUY | FashionShopMsg, ShopMsg |  |
| 5155 | 0x1423 | U_C_ARMY_RECRUITED | ArmyPawnInfoMsg |  |
| 5156 | 0x1424 | U_C_ARMY_EDIT | ArmyPawnInfoMsg |  |
| 5157 | 0x1425 | U_C_ARMY_DEMOBPAWN | ArmyPawnInfoMsg |  |
| 5158 | 0x1426 | U_C_ARMY_UPGRADEPAWN | ArmyPawnInfoMsg |  |
| 5160 | 0x1428 | U_C_ARMY_ATTACK | MapPhysicAttackMsg |  |
| 5161 | 0x1429 | U_C_ARMY_RETURNHOME | PayTypeMsg |  |
| 5167 | 0x142F | U_C_HERO_SETFASTKEY | HeroFastKeyMsg |  |
| 5170 | 0x1432 | U_C_HERO_RESETPOINT | (vazio) |  |
| 5172 | 0x1434 | U_C_BUILDING_ORDER_QUICK | BuildingReqMsg |  |
| 5173 | 0x1435 | U_C_BUIDLING_TRANS_COOL | PayTypeMsg |  |
| 5174 | 0x1436 | U_C_BUILDING_UPENERGY | PayTypeMsg |  |
| 5175 | 0x1437 | U_C_BUILDING_ORDERADD | PayTypeMsg |  |
| 5176 | 0x1438 | U_C_BUILDING_TRANSCASTLE | CastleReqMsg |  |
| 5178 | 0x143A | U_C_TREE_PICK | BuildingReqMsg |  |
| 5179 | 0x143B | U_C_UNOCCPWILDLAND | BuildingReqMsg |  |
| 5180 | 0x143C | U_C_CAMPAIGN_FINISH | CampaignReqMsg |  |
| 5181 | 0x143D | U_C_ARMY_UPDATE_GRID | OutercityReqMsg |  |
| 5184 | 0x1440 | C_HERO_SKILLPOINT_RESET | PayTypeMsg |  |
| 5185 | 0x1441 | C_HERO_SKILL_UPGRADE | HeroAddPointReqMsg |  |
| 5187 | 0x1443 | C_TALENT_GRADE_UP | TalentUpGradeMsg |  |
| 5633 | 0x1601 | C_FAST_USE_BLOOD | ShopMsg |  |
| 8196 | 0x2004 | C_NODE_LOCKSTATE | NodeLockReqMsg |  |
| 8197 | 0x2005 | U_C_CONSORTIA_ROBOTJOIN | (vazio) |  |
| 8198 | 0x2006 | C_BAG_USESMALLBUGLE | ChatChannelMsg |  |
| 8199 | 0x2007 | C_BAG_EQUIPLOOK | DetailReqMsg |  |
| 8200 | 0x2008 | C_SIMPLEUSER_INFO | InfoReqMsg |  |
| 8201 | 0x2009 | C_PHYSICLIST_BYGRID | PhysicUpdateReqMsg |  |
| 8202 | 0x200A | C_BUILDING_CREATE | BuildingOptionReqMsg |  |
| 8203 | 0x200B | C_BUILDING_UPGRADE | BuildingOptionReqMsg |  |
| 8205 | 0x200D | U_C_MAIL_SEND | MailSendReqMsg |  |
| 8206 | 0x200E | U_C_MAIL_DEL | MailDelReqMsg |  |
| 8207 | 0x200F | U_C_CONSORTIAUSER_LIST | (vazio) |  |
| 8208 | 0x2010 | U_C_CONSORTIA_OFFER_LIST | ConsortiaOfferReqMsg |  |
| 8209 | 0x2011 | U_C_INVITEINFO_LIST | (vazio) |  |
| 8210 | 0x2012 | U_C_EVENT_LIST | (vazio) |  |
| 8211 | 0x2013 | U_C_DUTY_LIST | (vazio) |  |
| 8212 | 0x2014 | U_C_CONSORTIA_INFO | ConsortiaMsg |  |
| 8213 | 0x2015 | U_C_CONSORTIA_SEARCH | SearchConditionMsg |  |
| 8214 | 0x2016 | U_C_CONSORTIA_INVITE_LIST | SearchConditionMsg |  |
| 8215 | 0x2017 | U_C_CONSORTIA_ALTERINFO | (vazio) |  |
| 8216 | 0x2018 | U_C_CONSORTIA_ADDFRESH | (vazio) |  |
| 8217 | 0x2019 | U_C_CONSORTIA_SITE | (vazio) |  |
| 8218 | 0x201A | U_C_SHOP_HASBUY | (vazio) |  |
| 8219 | 0x201B | C_TREE_FRIEND | FriendTreeReq |  |
| 8220 | 0x201C | C_BAG_ARRANGE | ArrangeReq |  |
| 8223 | 0x201F | U_C_CHECK_NICK | CheckNickMsg |  |
| 8224 | 0x2020 | C_LONIG_LOAD_REQ | PlayerDataMsg |  |
| 8231 | 0x2027 | C_REQ_FRIEND_FARM_STATE | FriendUserIdsMsg |  |
| 8234 | 0x202A | C_LEED_ADD | (vazio) |  |
| 8235 | 0x202B | C_LEED_FINISH | LeedFinishedReqMsg |  |
| 8241 | 0x2031 | C_CONSORTIA_VOTING_LIST | (vazio) |  |
| 8251 | 0x203B | C_FIGHT_SPECIAL_BOSS | (vazio) |  |
| 8253 | 0x203D | C_CHALLENGE | PlayerChallengeMsg |  |
| 8254 | 0x203E | C_MOVE_POS | PosMoveMsg |  |
| 8255 | 0x203F | C_PLAYER_REINFORCE | CampaignNodeMsg |  |
| 8256 | 0x2040 | C_CHALLENGEINFO_REQUEST | ChallengeRequestMsg |  |
| 8257 | 0x2041 | C_PLAYER_SEARCH | SimplePlayerSearchReqMsg |  |
| 8258 | 0x2042 | C_WORLD_BOSS_CMD | WorldBossMsg |  |
| 8259 | 0x2043 | C_WORLD_BOSS_REQ | WorldBossMsg |  |
| 8260 | 0x2044 | C_PLAYER_AASCHANGE | PlayerAASReqMsg |  |
| 8261 | 0x2045 | C_PLAYER_AASREFRESH | PlayerAASRefreshMsg |  |
| 8264 | 0x2048 | C_WORLDBOSS_PLAYER_LIVE | PayTypeMsg |  |
| 8265 | 0x2049 | C_QUICKCOOL_CHALLENGE_TIME | PayTypeMsg |  |
| 8266 | 0x204A | C_PLAYER_SIGN_CMD | (sem corpo) |  |
| 8267 | 0x204B | C_STAR_MOVE | StarMoveReqMsg |  |
| 8268 | 0x204C | C_STAR_PICK | StarPickReqMsg |  |
| 8269 | 0x204D | C_STAR_RAND | StarRandReqMsg |  |
| 8270 | 0x204E | C_STAR_BUY | PayTypeMsg |  |
| 8271 | 0x204F | C_WORLDBOSS_STATE | (vazio) |  |
| 8276 | 0x2054 | C_ARMYPOS_EDIT | ArmyFightPosEditMsg |  |
| 8277 | 0x2055 | C_CAMPIAGN_ARMYPOS_EDIT | ArmyFightPosEditListMsg |  |
| 8278 | 0x2056 | C_CAMPIAGN_ARMYPOS_REQ | (vazio) |  |
| 8279 | 0x2057 | C_LOAD_BUILD_ORDER | (sem corpo) |  |
| 8281 | 0x2059 | C_BUILDING_INIT | (vazio) |  |
| 8282 | 0x205A | C_BATTER_COUNT | BatterLastInfoMsg |  |
| 8283 | 0x205B | C_EFFECT_STOP | EffectRemoveReqMsg |  |
| 8285 | 0x205D | C_FRIEND_REFUSE | (sem corpo) |  |
| 8286 | 0x205E | C_ROOM_REFUSE | (sem corpo) |  |
| 8287 | 0x205F | C_TAKE_OFFLINE_REWARD | OfflineRewardMsg |  |
| 8288 | 0x2060 | C_REWARD_ADD | RewardAddedMsg |  |
| 8289 | 0x2061 | C_REWARD_REMOVE | RewardRemovedMsg |  |
| 8290 | 0x2062 | C_REWARD_FRESH | RewardFreshReqMsg |  |
| 8291 | 0x2063 | C_REWARD_FINISH | RewardFinishedReqMsg |  |
| 8292 | 0x2064 | C_CANCEL_HANGUP | (sem corpo) |  |
| 8293 | 0x2065 | C_QUICK_HANGUP_TIME | PayTypeMsg |  |
| 8294 | 0x2066 | C_MATCH_REQUEST | (sem corpo) |  |
| 8295 | 0x2067 | C_HANGUP_ROOM_STATE | (sem corpo) |  |
| 8296 | 0x2068 | C_ENTER_TOWER | EnterTowerInfoMsg |  |
| 8297 | 0x2069 | C_TOWER_INFO | TowerInfoReqMsg |  |
| 8298 | 0x206A | C_REWARD_ARREST | RewardArrestMsg |  |
| 8299 | 0x206B | C_TOWER_RESET | TowerInfoReqMsg |  |
| 8300 | 0x206C | C_TOWER_LIVE | PayTypeMsg |  |
| 8301 | 0x206D | C_PLAYER_NODE_STATE | ?Message, PlayerNodeStateMsg |  |
| 8302 | 0x206E | C_GUIDE_FINISHED | (sem corpo) |  |
| 8320 | 0x2080 | C_LUCKY_FRFRESH | PlayerLuckyMsg |  |
| 8321 | 0x2081 | C_LUCKY_SWAP | PlayerLuckyMsg |  |
| 8322 | 0x2082 | C_LEED_CLIENT | ClientReqMsg |  |
| 8325 | 0x2085 | C_STAR_DATA_RESET | (vazio) |  |
| 8326 | 0x2086 | C_ARMY_POSATION | ArmyPositionMsg |  |
| 8327 | 0x2087 | C_GOLD_IMPOSE | (sem corpo) |  |
| 8328 | 0x2088 | C_ARMYPOS_REQUEST | (sem corpo) |  |
| 8329 | 0x2089 | C_TAKE_CHALLENGEREWARD | (vazio), ChallengeRankRewardMsg |  |
| 8330 | 0x208A | C_STAR_LOCK | StarLockReqMsg |  |
| 8331 | 0x208B | C_STAR_COMPOSE | StarComposeReqMsg |  |
| 8332 | 0x208C | C_ENTER_WARFIELD | WorldBossMsg |  |
| 8334 | 0x208E | C_WARFIELD_ATTACK | WarFieldAttackMsg |  |
| 8335 | 0x208F | C_CONSORTIA_SPEAK | ConditionSpeakMsg |  |
| 8336 | 0x2090 | C_ITEM_REFRESHFORRANDOM | SmithFreshReqMsg |  |
| 8337 | 0x2091 | C_WARORDER_REQUEST | (sem corpo) |  |
| 8338 | 0x2092 | C_WAR_MAXHP | (sem corpo) |  |
| 8339 | 0x2093 | C_ITEM_REFRESHFORREPLACE | (sem corpo) |  |
| 8340 | 0x2094 | C_ITEM_RESOLVE | (sem corpo) |  |
| 8341 | 0x2095 | C_STARSHOP_BUY | StarShopMsg |  |
| 8343 | 0x2097 | C_CONSORTIA_LINK | ConsortiaLinkReqMsg |  |
| 8344 | 0x2098 | C_ROOM_PWDCHANGE | RoomEditMsg |  |
| 8345 | 0x2099 | C_PLAYER_RENAME_REQ | PlayerRenameReqMsg |  |
| 8346 | 0x209A | C_BAG_REMOVE | ItemRemoveMsg |  |
| 8352 | 0x20A0 | C_USER_PIN_CHECK | UserPin |  |
| 8353 | 0x20A1 | C_CAPTAIN_SPEAK | CaptainSpeakMsg |  |
| 8448 | 0x2100 | C_MALL_SELL_ITEM | SellItemReqMsg |  |
| 8449 | 0x2101 | C_MALL_LIST_SELL | MallItemViewReqMsg |  |
| 8450 | 0x2102 | C_MALL_PLAYER_ITEMS | MallItemViewReqMsg |  |
| 8451 | 0x2103 | C_MALL_AUCTION | AuctionItemReqMsg |  |
| 8452 | 0x2104 | C_MALL_LIST_AUCTION | MallItemViewReqMsg |  |
| 8453 | 0x2105 | C_MALL_FIX_AUCTION | AuctionItemReqMsg |  |
| 8454 | 0x2106 | C_MALL_CANCEL_SELL | AuctionItemReqMsg |  |
| 8455 | 0x2107 | C_COMPREHEND | ComprehendMsg |  |
| 8456 | 0x2108 | C_SAVESPECIAL | ComprehendMsg |  |
| 8457 | 0x2109 | C_MALL_SEARCH | SearchItemReqMsg |  |
| 8464 | 0x2110 | C_ITEM_REFRESHPROPERTY | RefreshPropertyReqMsg |  |
| 8465 | 0x2111 | U_C_ROOM_FIND | RoomReqMsg |  |
| 8466 | 0x2112 | C_REFININGSOUL_FRFRESH | PlayerRefiningSoulMsg |  |
| 8467 | 0x2113 | C_REFININGSOUL_SWAP | PlayerRefiningSoulMsg |  |
| 8470 | 0x2116 | C_WORLDBOSS_BUFFER | WorldBossBufferMsg |  |
| 8471 | 0x2117 | C_ENTER_GUILDCAMPAIGN | (sem corpo) |  |
| 8472 | 0x2118 | C_REQUEST_GUILDCHALLENGE | (sem corpo) |  |
| 8473 | 0x2119 | C_GUILDTEAM_PLAYER_EDIT | TeamEditMsg |  |
| 8477 | 0x211D | C_REQUEST_GUILDLIST | (sem corpo) |  |
| 8479 | 0x211F | C_ACTIVE_SECONDSKILL | PayTypeMsg |  |
| 8480 | 0x2120 | C_CHANGE_SKILL | HeroSkillChangeMsg |  |
| 8481 | 0x2121 | C_CONSORTIA_VOTING | ConsortiaVotingReqMsg |  |
| 8482 | 0x2122 | C_SHOPITEM_BUY | ShopItemBuyMsg |  |
| 8483 | 0x2123 | C_SHOPITEM_FRESH | ShopFreshReqMsg |  |
| 8484 | 0x2124 | C_BAG_USESTORE | ItemUseStoreReqMsg |  |
| 8488 | 0x2128 | C_WORLDMAP_PVPFIGHT | PlayerChallengeMsg |  |
| 8489 | 0x2129 | C_BLESSING_ALTER | (sem corpo) |  |
| 8496 | 0x2130 | C_PLAYER_RELOGIN_CMD | TakeLoginReward |  |
| 8505 | 0x2139 | C_VIP_BOX_DROP | (vazio) |  |
| 8513 | 0x2141 | C_VIP_OPEN | VipOpenInfoMsg |  |
| 8514 | 0x2142 | C_CHECK_CODE | CheckImageMsg |  |
| 8516 | 0x2144 | C_CHECK_SHOW_CODE | CheckImageMsg |  |
| 8518 | 0x2146 | C_CLICKDATALIST | (vazio) |  |
| 8519 | 0x2147 | C_VIPROULETTE | VipRouletteMsg |  |
| 8521 | 0x2149 | C_VIP_COIN_OPEN | (vazio) |  |
| 8524 | 0x214C | C_CHECK_SEND | CheckSend |  |
| 8525 | 0x214D | C_HANGUP_PVP | HangupAttackMsg |  |
| 8526 | 0x214E | C_OPRATE_REPLACEMENTS | OprateReplacemntMsg |  |
| 8528 | 0x2150 | C_CAMPAIGN_SWEEP | CampaignSweepReq |  |
| 8529 | 0x2151 | C_MOUNT_EDIT, C_MOUNT_OP | MountEditMsg |  |
| 8530 | 0x2152 | C_MOUNT_AVATARLIST | (sem corpo) |  |
| 8534 | 0x2156 | C_QUESTIONNARIE_ANSWER | QuestionDataRspMsg |  |
| 8535 | 0x2157 | C_CANCEL_TRANS | (sem corpo) |  |
| 8537 | 0x2159 | C_ENTER_CONSORTIA_FAM | (vazio) |  |
| 8538 | 0x215A | C_ITEM_TRANSFORM | StoreReqMsg |  |
| 8540 | 0x215C | C_KING_CONTRACT | KingContractBuyMsg |  |
| 8541 | 0x215D | C_OPEN_CONSORTIA__ALTAR | ConsortiaAltarOpenReqMsg |  |
| 8542 | 0x215E | C_ENTER_CONSORTIA_ALTAR | (vazio) |  |
| 8544 | 0x2160 | U_C_CONSORTIA_GROUP_PLACARD | ConsortiaMsg |  |
| 8545 | 0x2161 | C_CONSORTIA_QUICK | PayTypeMsg |  |
| 8546 | 0x2162 | C_GUILD_GROUP | (sem corpo) |  |
| 8547 | 0x2163 | C_GUILD_BUYBUFFER | GuildMsg |  |
| 8548 | 0x2164 | C_PLAYER_REFAIRE | GuildMsg |  |
| 8549 | 0x2165 | ARRIVE_ALTAR | ArriveAltarReqMsg |  |
| 8550 | 0x2166 | C_CONSORTIA_ALTAR_GETBUFF | (vazio) |  |
| 8562 | 0x2172 | C_CASTLE_TIME_CANCEL | EffectRemoveReqMsg |  |
| 8565 | 0x2175 | C_CALL_TREE | (vazio) |  |
| 8566 | 0x2176 | C_FAM_BUFFER | (vazio) |  |
| 8574 | 0x217E | C_REBATE_DATA | RebateOpMsg |  |
| 8577 | 0x2181 | C_CONSORTIA_BOX_CHECK | (vazio) |  |
| 8578 | 0x2182 | C_CONSORTIA_BOX_SEND_CONFIRM | ConsortiaTreasureBoxMsg |  |
| 8579 | 0x2183 | C_CONSORTIA_BOX_SEND_INFO | ConsortiaTreasureBoxMsg |  |
| 8580 | 0x2184 | C_PAWN_CHANGE | PawnChangeMsg |  |
| 8582 | 0x2186 | C_BUY_TRIAL | TrialInfoMsg |  |
| 8586 | 0x218A | C_SUMACTIVE_GATE | SumActiveGetPackageMsg |  |
| 8590 | 0x218E | C_TAKE_CROSS_SCORE_REWARD | (vazio), ChallengeRankRewardMsg |  |
| 8592 | 0x2190 | C_FASHION_SHOP_BUY | FashionShopMsg, ShopMsg |  |
| 8593 | 0x2191 | C_CONSORTIA_ALTAR_BUY_SCENE | ConsortiaAltarOpenReqMsg |  |
| 8594 | 0x2192 | C_FASHION_COMPOSE | StoreReqMsg |  |
| 8595 | 0x2193 | C_FASHION_SWITCH | FashionMsg, StoreReqMsg |  |
| 8597 | 0x2195 | C_APPELL_EXCHANGE | AppellExchangeMsg |  |
| 8598 | 0x2196 | C_CC | ?Message, SimplePropertyMsg |  |
| 8599 | 0x2197 | C_CHECK_WARFIELD_COUNT | CampaignReqMsg |  |
| 8604 | 0x219C | C_BOTTLE_OP | BottleOpMsg |  |
| 8605 | 0x219D | U_C_HERO_RUNE_OP | HeroRuneOpMsg |  |
| 8608 | 0x21A0 | C_VEHICLE_QUICK_PLAY | (sem corpo) |  |
| 8609 | 0x21A1 | C_VEHICLE_QUICK_PLAY_CANCEL | (sem corpo) |  |
| 8610 | 0x21A2 | C_VEHICLE_LEAVE_CAMPAIGN | (sem corpo) |  |
| 8611 | 0x21A3 | C_VEHICLE_CHOOSE_VEHICLE | CampaignReqMsg |  |
| 8615 | 0x21A7 | C_VEHICLE_MOVE | VehicleMoveMsg |  |
| 8616 | 0x21A8 | C_VEHICLE_ATTACK | VehicleAttackReqMsg |  |
| 8617 | 0x21A9 | C_VEHICLE_PICK_PROP | VehiclePickPropMsg |  |
| 8619 | 0x21AB | C_ACTIVE_VEHICLE | SimplePropertyMsg |  |
| 8620 | 0x21AC | C_PLAYER_AAS_SWITCH_CHANGE | PlayerAASRefreshMsg |  |
| 8621 | 0x21AD | C_PLAYER_PET_OP | PlayerPetOpMsg |  |
| 8623 | 0x21AF | C_SEND_CROSS_BIGBUGLE | CrossBigBugleMsg |  |
| 8624 | 0x21B0 | C_BAG_BATCH_SELL | ItemSellReqMsg |  |
| 8625 | 0x21B1 | C_FASHION_INFO | (vazio) |  |
| 8626 | 0x21B2 | U_C_FATE_TRAIN | FateEditMsg |  |
| 8627 | 0x21B3 | C_FATE_TURN | FateEditMsg |  |
| 8628 | 0x21B4 | C_FATE_REQUEST | (sem corpo) |  |
| 8629 | 0x21B5 | C_GAME_STORY_REQUEST | GameStoryMsg |  |
| 8630 | 0x21B6 | C_GAME_STORY_REWARD | (vazio) |  |
| 8631 | 0x21B7 | C_FASHION_SPECIAL | FashionMsg |  |
| 8632 | 0x21B8 | C_FLASH_SALE_FRESH | ?Message |  |
| 8633 | 0x21B9 | C_ENTER_MINE_FIELD | (vazio), ChallengeRankRewardMsg |  |
| 8634 | 0x21BA | C_BACK_PLAYER_REWARD | (vazio), ChallengeRankRewardMsg |  |
| 8635 | 0x21BB | C_CHALLENGE_SELF | QuestInfo |  |
| 8636 | 0x21BC | C_UPDATE_AREA | (vazio) |  |
| 8637 | 0x21BD | C_GET_AREA_REWARD | (vazio) |  |
| 8638 | 0x21BE | C_GET_BUGLE | (vazio) |  |
| 8639 | 0x21BF | C_BUGLE_ROULETTE | VipRouletteMsg |  |
| 8640 | 0x21C0 | C_BUGLE_OPEN | (vazio) |  |
| 8641 | 0x21C1 | C_DRAGON_FEED | FateEditMsg |  |
| 8642 | 0x21C2 | C_DRAGON_REQUEST | (sem corpo) |  |
| 8643 | 0x21C3 | C_DRAGON_TRANSFER | (sem corpo) |  |
| 8644 | 0x21C4 | C_MOULD_ITEM | PayTypeMsg |  |
| 8645 | 0x21C5 | C_GROUPON | ShopMsg |  |
| 8688 | 0x21F0 | C_PLAYER_SPACE_ENTER | SimplePropertyMsg |  |
| 8689 | 0x21F1 | C_PLAYER_SPACE_LEAVE | SimplePropertyMsg |  |
| 8690 | 0x21F2 | C_PLAYER_SPACE_MOVE | SpacePlayerMoveMsg |  |
| 8692 | 0x21F4 | C_PLAYER_SPACE_NODE_TRIGGER | SimplePropertyMsg |  |
| 8693 | 0x21F5 | C_BUY_DISCOUNT | ShopMsg |  |
| 8694 | 0x21F6 | C_ENTER_PETISLAND | CampaignReqMsg |  |
| 8699 | 0x21FB | C_NEW_GUILD_FIGHT | (vazio) |  |
| 8700 | 0x21FC | C_CHECK_MOVEABLE | (vazio) |  |
| 8701 | 0x21FD | C_GET_SPACE_PLAYER_ARMY_INFO | SpacePlayerArmyInfoReqMsg |  |
| 8702 | 0x21FE | C_GET_PLAYER_PET_INFO | PlayerPetOpMsg |  |
| 8703 | 0x21FF | C_U_ACTIVE_DEPOSIT | DepositActiveMsg |  |
| 8705 | 0x2201 | C_SMALL_BUGLE_FREE_COUNT | CampaignReqMsg |  |
| 8710 | 0x2206 | C_ENTER_REQUEST | (vazio) |  |
| 8711 | 0x2207 | C_LOAD_LORDS_MAINBORAD | (vazio) |  |
| 8714 | 0x220A | C_REQUEST_START | (vazio) |  |
| 8715 | 0x220B | C_REQUEST_FINAL_ORDERLIST | (vazio) |  |
| 8716 | 0x220C | C_BET_ADDLORDS | SimplePropertyMsg |  |
| 8717 | 0x220D | C_LEAVE_LORDS | (vazio) |  |
| 8718 | 0x220E | C_REQUEST_BET_LIST | (vazio) |  |
| 8720 | 0x2210 | C_TAKE_FINAL_REWARD | (vazio) |  |
| 8721 | 0x2211 | C_REQUEST_LOCAL_FINAL_ORDER | (vazio) |  |
| 8722 | 0x2212 | C_TAKE_360_REWARD | PrivilegeMsg |  |
| 8723 | 0x2213 | C_REQUEST_360_REWARD | (vazio) |  |
| 8724 | 0x2214 | C_CHALLENGE_PET | PlayerChallengeMsg |  |
| 8725 | 0x2215 | C_PET_CHALLENGE_FORMATION | PlayerPetMsg |  |
| 8726 | 0x2216 | C_PET_CHALLENGE_SKILL | PetInfoMsg |  |
| 8727 | 0x2217 | C_PET_CHALLENGE_END_BATTLE | BattleReqMsg |  |
| 8728 | 0x2218 | C_PET_RANK_REWARD | RankRewardMsg |  |
| 8729 | 0x2219 | C_REPEAT_REWARD_FINISH | (sem corpo) |  |
| 8730 | 0x221A | C_REPEAT_REWARD_FINISH_IMMEDIATELY | SimplePropertyMsg |  |
| 8731 | 0x221B | C_REPEAT_REWARD_UPDATE_FINISH | (sem corpo) |  |
| 8732 | 0x221C | C_TAKE_REPEAT_REWARD | (sem corpo) |  |
| 8733 | 0x221D | C_SPACE_COLLECTION_FINISHED | SimplePropertyMsg |  |
| 8734 | 0x221E | C_APPLY_INVITE_TEAM | SimplePropertyMsg |  |
| 8736 | 0x2220 | C_CHANGE_CAPTAIN | SimplePropertyMsg |  |
| 8737 | 0x2221 | C_EDIT_TEAM_FIGHT_POS | MemberFightPosListMsg |  |
| 8738 | 0x2222 | C_INVITE_TEAM | SimplePropertyMsg |  |
| 8739 | 0x2223 | C_KICK_TEAM_MEMBER | SimplePropertyMsg |  |
| 8740 | 0x2224 | C_LEAVE_TEAM_FOR_NOW | (sem corpo) |  |
| 8741 | 0x2225 | C_QUIT_TEAM | (sem corpo) |  |
| 8742 | 0x2226 | C_BATTLEGUARD_OP | HeroWatchOpMsg |  |
| 8743 | 0x2227 | C_CONSORTIAFARM_OPEN_LORDSNODE | (vazio) |  |
| 8744 | 0x2228 | C_TREASUREMAP_OP | PlayerTreasureMsg |  |
| 8745 | 0x2229 | C_TREASUREMAP_BATTLE_REINFORCE | GuildMsg |  |
| 8746 | 0x222A | C_TEAM_REFUSE, C_TREASUREMAP_REQUEST | (sem corpo) |  |
| 8747 | 0x222B | C_ENTER_CASTLE | SimplePropertyMsg |  |
| 8748 | 0x222C | C_LOTTERY_REWARD | (vazio) |  |
| 8749 | 0x222D | C_SERVEN_LEAD | GetRewardMsg |  |
| 8750 | 0x222E | C_LOTTERY_REQUEST | (vazio) |  |
| 8751 | 0x222F | C_FRESHMAN_DEPOSIT | DepositActiveMsg |  |
| 8752 | 0x2230 | C_TOLLGATE_GET_REWARD | (vazio) |  |
| 8753 | 0x2231 | C_TOLLGATE_REQUEST | PlayerChallengeMsg |  |
| 8754 | 0x2232 | C_TOLLGATE_SCORE | (vazio) |  |
| 8755 | 0x2233 | C_TOLLGATE_REQUEST_ATTACK | PlayerChallengeMsg |  |
| 8756 | 0x2234 | C_VIPCUSTOM_ADD | (sem corpo) |  |
| 8759 | 0x2237 | C_marriage_REQUEST | MarriageOpMsg |  |
| 8760 | 0x2238 | C_MARRIAGE_CAMPAIGN_REQUEST | MarriageOpMsg |  |
| 8773 | 0x2245 | C_MARRIAGE_TREE_REQUEST | MarriageOpMsg |  |
| 8774 | 0x2246 | C_MARRIAGE_TASK_REQUEST | MarriageOpMsg |  |
| 8778 | 0x224A | C_CROSSGUILD_TEAM_EDIT | CrossGuildMsg |  |
| 8779 | 0x224B | C_CROSSGUILD_SIGNUP | (sem corpo) |  |
| 8781 | 0x224D | C_FASHION_APPLRAISAL | FashionMsg |  |
| 8782 | 0x224E | C_CROSSGUILD_GROUP | CrossGuildMsg |  |
| 8783 | 0x224F | C_ENTER_CROSSGUILD | (sem corpo) |  |
| 8802 | 0x2262 | C_MARRIAGE_HEART | MarriageOpMsg |  |
| 8806 | 0x2266 | C_VICEPASSWORD | VicePasswordMsg |  |
| 8809 | 0x2269 | C_LOCK_OR_UNLOCK | LockAndUnlockMsg |  |
| 8819 | 0x2273 | C_RENTAL_BAG_OP | RentalBagOpReqMsg |  |
| 8843 | 0x228B | C_NEW_MOUNT_ACTIVE | (vazio) |  |
| 8866 | 0x22A2 | C_REQUEST_CHARGE_REWARD | (vazio) |  |
| 8975 | 0x230F | C_MATE_LORDS_SIGNUP | (vazio) |  |
| 8976 | 0x2310 | C_MATE_LORDS_ROOM_CREATE | (vazio) |  |
| 8979 | 0x2313 | C_MATE_LORDS_MAININFO | (vazio) |  |
| 8981 | 0x2315 | C_MATE_LORDS_INSPIRE | (vazio) |  |
| 8985 | 0x2319 | C_BATTLE_VIEW | BattleViewMsg |  |
| 8994 | 0x2322 | C_NEW_YEAR_BOX_ACTIVE | SimplePropertyMsg |  |
| 9500 | 0x251C | C_SLOT_ACTIVE_REQ | SlotActiveRequest |  |
| 9501 | 0x251D | C_ANSWER_REQUEST_OPTION | AnswerquestionReqMsg |  |
| 9502 | 0x251E | C_SEEK_REQ | PlayerSeekInfoMsg |  |
| 9503 | 0x251F | C_RECOVER | RecoverReqMsg |  |
| 9504 | 0x2520 | C_MULITY_CAMPAIGN_REQUEST | SimplePropertyMsg |  |
| 9505 | 0x2521 | C_POWCARD_REQ | PowCardReqMsg |  |
| 9506 | 0x2522 | C_CASTLE_ATTACK | OutercityReqMsg |  |
| 9507 | 0x2523 | C_FISH_POOL | FreshPoolMsg |  |
| 9508 | 0x2524 | C_GET_GEMMAZE_INFO | (sem corpo) |  |
| 9509 | 0x2525 | C_GEMMAZE_GEMMOVE | GemMoveMsg |  |
| 9510 | 0x2526 | C_GEMMAZE_INVITE | GemMoveInviteMsg |  |
| 9513 | 0x2529 | C_GEMMAZE_GETREWARDBOX | GetRewardBoxMsg |  |
| 9515 | 0x252B | C_GEMMAZE_INVITE_OP | GemInviteOpMsg |  |
| 9516 | 0x252C | C_GEMMAZE_BUYTIMES | GemMazeBuyTimesMsg |  |
| 9517 | 0x252D | C_GEMMAZE_GETALL | (sem corpo) |  |
| 9520 | 0x2530 | C_GOLDENROAD_FRESH | GoldenRoadClientRequestMsg |  |
| 9521 | 0x2531 | C_GOLDENROAD_CASTDICE | GoldenRoadClientRequestMsg |  |
| 9522 | 0x2532 | C_GOLDENROAD_BROADCAST | GoldenRoadClientRequestMsg |  |
| 9523 | 0x2533 | C_LEAD_EXTRACT | LeadRewardMsg |  |
| 9525 | 0x2535 | C_MAPBOSS_DATAS | MapBossQuestMsg |  |
| 9526 | 0x2536 | C_MAPBOX_PICK | ArmyBoxMsg |  |
| 9550 | 0x254E | C_ICON_NUM | IconNumMsgList |  |
| 9591 | 0x2577 | C_MAIL_CHECK | MailCheckMsg |  |
| 9602 | 0x2582 | C_REQUEST_CONSUM_REWARD | ChargeRewardMsg |  |
| 9610 | 0x258A | C_LUCK_EXCHANGE | LuckExchangeOpMsg |  |
| 9611 | 0x258B | C_MATE_SKILL_SHOP | AltarShopListMsg |  |
| 9638 | 0x25A6 | C_CHAIRS_CLIENT_OP | ChairsListMsg |  |
| 9645 | 0x25AD | C_CCCACTIVE_CLIENTOP | OreActiveClientOpMsg, SuperSigninCardReqMsg |  |
| 10003 | 0x2713 | DEBUG_BATTLE | BattleCreateMsg |  |
| 10007 | 0x2717 | U_B_USER_LOADOVER | LoadOverMsg |  |
| 10008 | 0x2718 | U_B_HERO_ORDER | UseSkillMsg |  |
| 10010 | 0x271A | U_B_USR_STOP_CMD | BattleReqMsg |  |
| 10015 | 0x271F | U_B_QTE | QteMsg |  |
| 10016 | 0x2720 | U_B_FIGHT_MODE | AttackModeMsg |  |
| 10018 | 0x2722 | B_REINFORCE_LOADOVER | LoadOverMsg |  |
| 10020 | 0x2724 | B_SET_ATUO_ATTACK | AttackModeMsg |  |
| 10022 | 0x2726 | B_PAUSE_FINISHED | BattleReqMsg |  |
| 10497 | 0x2901 | B_REMOVE_BATTLE | BattleReqMsg |  |
| 10499 | 0x2903 | B_USE_ITEM | BattleItemMsg |  |
| 10507 | 0x290B | B_USE_TRIAL | BattleItemMsg |  |
| 10509 | 0x290D | B_USE_MARRSKILL | BattleItemMsg |  |
| 10516 | 0x2914 | B_CHILD_ORDER | UseSkillMsg |  |
| 15003 | 0x3A9B | U_CH_ADD_RELATIONSHIP | FriendRelationMsg |  |
| 15004 | 0x3A9C | U_CH_REMOVE_RELATIONSHIP | FriendRelationMsg |  |
| 15005 | 0x3A9D | U_CH_CHANNEL_CHA | ChatChannelMsg |  |
| 15012 | 0x3AA4 | U_CH_FRIENDADD_CONFIRM | FriendRelationMsg |  |
| 15013 | 0x3AA5 | U_CH_RECOMMENDLIST | (sem corpo) |  |
| 15017 | 0x3AA9 | CH_TREE_WATER | BuildingReqMsg |  |
| 15023 | 0x3AAF | CH_PRIVATE_CHAT | ChatFriendMsg |  |
| 15025 | 0x3AB1 | CH_ADD_GROUP | FriendGroupMsg |  |
| 15026 | 0x3AB2 | CH_DEL_GROUP | FriendGroupMsg |  |
| 15027 | 0x3AB3 | CH_RENAME_GROUP | FriendGroupMsg |  |
| 15028 | 0x3AB4 | CH_FRIEND_MOVE | MoveFriendReqMsg |  |
| 15029 | 0x3AB5 | CH_EXCHANGE_STATE | ChatStateMsg |  |
| 15033 | 0x3AB9 | CH_SNS_UPDATE | SNSInfoMsg |  |
| 15036 | 0x3ABC | CH_SNSINFO_RESET | (sem corpo) |  |
| 15038 | 0x3ABE | CH_SIMPLEUSER_INFO | InfoReqMsg |  |
| 15042 | 0x3AC2 | CH_FRIEND_SEARCH | FriendSearchConditionReqMsg |  |
| 15043 | 0x3AC3 | CH_CHAT_STATE | RecentContractsStateReqMsg |  |
| 15044 | 0x3AC4 | CH_FARM_OPER_CHECK | FarmOperReqMsg |  |
| 15049 | 0x3AC9 | CH_MARRIAGE_BUY_SPEC | MarriageOpMsg |  |
| 20001 | 0x4E21 | U_G_LOGIN_GATEWAY | LoginReqMsg |  |
| 20008 | 0x4E28 | C_SYNCHRONIZED_TIME | (sem corpo) |  |
| 20009 | 0x4E29 | G_ACCELERATOR | SimplePropertyMsg |  |
| 20010 | 0x4E2A | C_CHECK_ACCELERATOR | (sem corpo) |  |
| 25024 | 0x61C0 | CR_CHANNEL_CHAT | ChatChannelMsg |  |
| 25096 | 0x6208 | CR_WARFIELD_CHAT | ChatChannelMsg |  |
| 25097 | 0x6209 | CR_WARFIELD_USER_INFO | DetailReqMsg |  |
| 25111 | 0x6217 | C_EXIT_VEHICLE_NODE | WarFieldAttackMsg |  |
| 25112 | 0x6218 | C_MAP_VEHICLE_ATTACK | VehicleAttackReqMsg |  |
