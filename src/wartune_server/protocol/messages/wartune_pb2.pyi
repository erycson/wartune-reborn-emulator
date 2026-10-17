from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ActiveData(_message.Message):
    __slots__ = ("packdata", "value", "activeId", "isShow", "type", "activeCharge", "consumeMsg")
    PACKDATA_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    ACTIVEID_FIELD_NUMBER: _ClassVar[int]
    ISSHOW_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    ACTIVECHARGE_FIELD_NUMBER: _ClassVar[int]
    CONSUMEMSG_FIELD_NUMBER: _ClassVar[int]
    packdata: _containers.RepeatedCompositeFieldContainer[PackageData]
    value: int
    activeId: str
    isShow: bool
    type: int
    activeCharge: int
    consumeMsg: _containers.RepeatedCompositeFieldContainer[ConsumeInfoMsg]
    def __init__(self, packdata: _Optional[_Iterable[_Union[PackageData, _Mapping]]] = ..., value: _Optional[int] = ..., activeId: _Optional[str] = ..., isShow: _Optional[bool] = ..., type: _Optional[int] = ..., activeCharge: _Optional[int] = ..., consumeMsg: _Optional[_Iterable[_Union[ConsumeInfoMsg, _Mapping]]] = ...) -> None: ...

class ActiveParamMsg(_message.Message):
    __slots__ = ("level", "costDiamond", "costContract", "getBindingDia", "harvestCount", "itemInfos", "getInfos")
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    COSTDIAMOND_FIELD_NUMBER: _ClassVar[int]
    COSTCONTRACT_FIELD_NUMBER: _ClassVar[int]
    GETBINDINGDIA_FIELD_NUMBER: _ClassVar[int]
    HARVESTCOUNT_FIELD_NUMBER: _ClassVar[int]
    ITEMINFOS_FIELD_NUMBER: _ClassVar[int]
    GETINFOS_FIELD_NUMBER: _ClassVar[int]
    level: int
    costDiamond: int
    costContract: int
    getBindingDia: int
    harvestCount: int
    itemInfos: _containers.RepeatedCompositeFieldContainer[GItemInfoMsg]
    getInfos: _containers.RepeatedCompositeFieldContainer[GetItemInfosMsg]
    def __init__(self, level: _Optional[int] = ..., costDiamond: _Optional[int] = ..., costContract: _Optional[int] = ..., getBindingDia: _Optional[int] = ..., harvestCount: _Optional[int] = ..., itemInfos: _Optional[_Iterable[_Union[GItemInfoMsg, _Mapping]]] = ..., getInfos: _Optional[_Iterable[_Union[GetItemInfosMsg, _Mapping]]] = ...) -> None: ...

class ActiveRspInfo(_message.Message):
    __slots__ = ("activeId", "title", "contents", "awardContent", "description", "actionTimeContent", "consortia", "grades", "sort", "endDate", "startDate")
    ACTIVEID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    CONTENTS_FIELD_NUMBER: _ClassVar[int]
    AWARDCONTENT_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    ACTIONTIMECONTENT_FIELD_NUMBER: _ClassVar[int]
    CONSORTIA_FIELD_NUMBER: _ClassVar[int]
    GRADES_FIELD_NUMBER: _ClassVar[int]
    SORT_FIELD_NUMBER: _ClassVar[int]
    ENDDATE_FIELD_NUMBER: _ClassVar[int]
    STARTDATE_FIELD_NUMBER: _ClassVar[int]
    activeId: str
    title: str
    contents: str
    awardContent: str
    description: str
    actionTimeContent: str
    consortia: int
    grades: int
    sort: int
    endDate: str
    startDate: str
    def __init__(self, activeId: _Optional[str] = ..., title: _Optional[str] = ..., contents: _Optional[str] = ..., awardContent: _Optional[str] = ..., description: _Optional[str] = ..., actionTimeContent: _Optional[str] = ..., consortia: _Optional[int] = ..., grades: _Optional[int] = ..., sort: _Optional[int] = ..., endDate: _Optional[str] = ..., startDate: _Optional[str] = ...) -> None: ...

class ActiveRspMsg(_message.Message):
    __slots__ = ("activeRspInfo",)
    ACTIVERSPINFO_FIELD_NUMBER: _ClassVar[int]
    activeRspInfo: _containers.RepeatedCompositeFieldContainer[ActiveRspInfo]
    def __init__(self, activeRspInfo: _Optional[_Iterable[_Union[ActiveRspInfo, _Mapping]]] = ...) -> None: ...

class AdditionMsg(_message.Message):
    __slots__ = ("masterType", "power", "agility", "intellect", "physique", "createDate", "expirtDate", "description", "isExist")
    MASTERTYPE_FIELD_NUMBER: _ClassVar[int]
    POWER_FIELD_NUMBER: _ClassVar[int]
    AGILITY_FIELD_NUMBER: _ClassVar[int]
    INTELLECT_FIELD_NUMBER: _ClassVar[int]
    PHYSIQUE_FIELD_NUMBER: _ClassVar[int]
    CREATEDATE_FIELD_NUMBER: _ClassVar[int]
    EXPIRTDATE_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    ISEXIST_FIELD_NUMBER: _ClassVar[int]
    masterType: int
    power: int
    agility: int
    intellect: int
    physique: int
    createDate: str
    expirtDate: str
    description: str
    isExist: bool
    def __init__(self, masterType: _Optional[int] = ..., power: _Optional[int] = ..., agility: _Optional[int] = ..., intellect: _Optional[int] = ..., physique: _Optional[int] = ..., createDate: _Optional[str] = ..., expirtDate: _Optional[str] = ..., description: _Optional[str] = ..., isExist: _Optional[bool] = ...) -> None: ...

class AltarCampaignReportMsg(_message.Message):
    __slots__ = ("altarDurability", "waveNum", "monsterCount", "buffType", "hurtOrder", "leftStartTime", "userBuffType", "skill")
    ALTARDURABILITY_FIELD_NUMBER: _ClassVar[int]
    WAVENUM_FIELD_NUMBER: _ClassVar[int]
    MONSTERCOUNT_FIELD_NUMBER: _ClassVar[int]
    BUFFTYPE_FIELD_NUMBER: _ClassVar[int]
    HURTORDER_FIELD_NUMBER: _ClassVar[int]
    LEFTSTARTTIME_FIELD_NUMBER: _ClassVar[int]
    USERBUFFTYPE_FIELD_NUMBER: _ClassVar[int]
    SKILL_FIELD_NUMBER: _ClassVar[int]
    altarDurability: int
    waveNum: int
    monsterCount: int
    buffType: int
    hurtOrder: _containers.RepeatedCompositeFieldContainer[HurtOrderMsg]
    leftStartTime: int
    userBuffType: int
    skill: _containers.RepeatedCompositeFieldContainer[AltarCampaignSkillMsg]
    def __init__(self, altarDurability: _Optional[int] = ..., waveNum: _Optional[int] = ..., monsterCount: _Optional[int] = ..., buffType: _Optional[int] = ..., hurtOrder: _Optional[_Iterable[_Union[HurtOrderMsg, _Mapping]]] = ..., leftStartTime: _Optional[int] = ..., userBuffType: _Optional[int] = ..., skill: _Optional[_Iterable[_Union[AltarCampaignSkillMsg, _Mapping]]] = ...) -> None: ...

class AltarCampaignSkillMsg(_message.Message):
    __slots__ = ("templateId", "cDTimer", "userId", "nickName", "consortiaId")
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    CDTIMER_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    CONSORTIAID_FIELD_NUMBER: _ClassVar[int]
    templateId: int
    cDTimer: int
    userId: int
    nickName: str
    consortiaId: int
    def __init__(self, templateId: _Optional[int] = ..., cDTimer: _Optional[int] = ..., userId: _Optional[int] = ..., nickName: _Optional[str] = ..., consortiaId: _Optional[int] = ...) -> None: ...

class AltarShopInfoMsg(_message.Message):
    __slots__ = ("templateId", "price", "leftCount", "maxCount", "skillTempId")
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    PRICE_FIELD_NUMBER: _ClassVar[int]
    LEFTCOUNT_FIELD_NUMBER: _ClassVar[int]
    MAXCOUNT_FIELD_NUMBER: _ClassVar[int]
    SKILLTEMPID_FIELD_NUMBER: _ClassVar[int]
    templateId: int
    price: int
    leftCount: int
    maxCount: int
    skillTempId: int
    def __init__(self, templateId: _Optional[int] = ..., price: _Optional[int] = ..., leftCount: _Optional[int] = ..., maxCount: _Optional[int] = ..., skillTempId: _Optional[int] = ...) -> None: ...

class AltarShopListMsg(_message.Message):
    __slots__ = ("op", "altarScore", "templateId", "skillTempId", "info")
    OP_FIELD_NUMBER: _ClassVar[int]
    ALTARSCORE_FIELD_NUMBER: _ClassVar[int]
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    SKILLTEMPID_FIELD_NUMBER: _ClassVar[int]
    INFO_FIELD_NUMBER: _ClassVar[int]
    op: int
    altarScore: int
    templateId: int
    skillTempId: int
    info: _containers.RepeatedCompositeFieldContainer[AltarShopInfoMsg]
    def __init__(self, op: _Optional[int] = ..., altarScore: _Optional[int] = ..., templateId: _Optional[int] = ..., skillTempId: _Optional[int] = ..., info: _Optional[_Iterable[_Union[AltarShopInfoMsg, _Mapping]]] = ...) -> None: ...

class AnswerquestionReqMsg(_message.Message):
    __slots__ = ("type", "count")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    type: int
    count: int
    def __init__(self, type: _Optional[int] = ..., count: _Optional[int] = ...) -> None: ...

class AppellExchangeMsg(_message.Message):
    __slots__ = ("appellId", "look")
    APPELLID_FIELD_NUMBER: _ClassVar[int]
    LOOK_FIELD_NUMBER: _ClassVar[int]
    appellId: int
    look: bool
    def __init__(self, appellId: _Optional[int] = ..., look: _Optional[bool] = ...) -> None: ...

class AppellInfoMsg(_message.Message):
    __slots__ = ("appellId", "isGet", "value", "validDate")
    APPELLID_FIELD_NUMBER: _ClassVar[int]
    ISGET_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    VALIDDATE_FIELD_NUMBER: _ClassVar[int]
    appellId: int
    isGet: bool
    value: str
    validDate: str
    def __init__(self, appellId: _Optional[int] = ..., isGet: _Optional[bool] = ..., value: _Optional[str] = ..., validDate: _Optional[str] = ...) -> None: ...

class AppellsMsg(_message.Message):
    __slots__ = ("appells",)
    APPELLS_FIELD_NUMBER: _ClassVar[int]
    appells: _containers.RepeatedCompositeFieldContainer[AppellInfoMsg]
    def __init__(self, appells: _Optional[_Iterable[_Union[AppellInfoMsg, _Mapping]]] = ...) -> None: ...

class ArmyArmyMsg(_message.Message):
    __slots__ = ("armyId", "playerId", "nickName", "mapId", "curPosX", "curPosY", "state", "type", "armyPawn", "simpleHeroInfo", "consortiaId", "consortiaName", "fightingCapacity", "gpOrder", "grades", "arm", "cloth", "job", "changeSharp", "heroTempId", "userIds", "geste", "isVip", "vipType", "mountTempId", "mountGrade", "wing", "serverName", "hat", "fashionArm", "fashionCloth", "hide", "appellid", "fateSkills", "petTempId", "petQuqlity", "petName")
    ARMYID_FIELD_NUMBER: _ClassVar[int]
    PLAYERID_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    MAPID_FIELD_NUMBER: _ClassVar[int]
    CURPOSX_FIELD_NUMBER: _ClassVar[int]
    CURPOSY_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    ARMYPAWN_FIELD_NUMBER: _ClassVar[int]
    SIMPLEHEROINFO_FIELD_NUMBER: _ClassVar[int]
    CONSORTIAID_FIELD_NUMBER: _ClassVar[int]
    CONSORTIANAME_FIELD_NUMBER: _ClassVar[int]
    FIGHTINGCAPACITY_FIELD_NUMBER: _ClassVar[int]
    GPORDER_FIELD_NUMBER: _ClassVar[int]
    GRADES_FIELD_NUMBER: _ClassVar[int]
    ARM_FIELD_NUMBER: _ClassVar[int]
    CLOTH_FIELD_NUMBER: _ClassVar[int]
    JOB_FIELD_NUMBER: _ClassVar[int]
    CHANGESHARP_FIELD_NUMBER: _ClassVar[int]
    HEROTEMPID_FIELD_NUMBER: _ClassVar[int]
    USERIDS_FIELD_NUMBER: _ClassVar[int]
    GESTE_FIELD_NUMBER: _ClassVar[int]
    ISVIP_FIELD_NUMBER: _ClassVar[int]
    VIPTYPE_FIELD_NUMBER: _ClassVar[int]
    MOUNTTEMPID_FIELD_NUMBER: _ClassVar[int]
    MOUNTGRADE_FIELD_NUMBER: _ClassVar[int]
    WING_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    HAT_FIELD_NUMBER: _ClassVar[int]
    FASHIONARM_FIELD_NUMBER: _ClassVar[int]
    FASHIONCLOTH_FIELD_NUMBER: _ClassVar[int]
    HIDE_FIELD_NUMBER: _ClassVar[int]
    APPELLID_FIELD_NUMBER: _ClassVar[int]
    FATESKILLS_FIELD_NUMBER: _ClassVar[int]
    PETTEMPID_FIELD_NUMBER: _ClassVar[int]
    PETQUQLITY_FIELD_NUMBER: _ClassVar[int]
    PETNAME_FIELD_NUMBER: _ClassVar[int]
    armyId: int
    playerId: int
    nickName: str
    mapId: int
    curPosX: int
    curPosY: int
    state: int
    type: int
    armyPawn: _containers.RepeatedCompositeFieldContainer[ArmyPawnInfoMsg]
    simpleHeroInfo: SimpleHeroInfoMsg
    consortiaId: int
    consortiaName: str
    fightingCapacity: int
    gpOrder: int
    grades: int
    arm: str
    cloth: str
    job: int
    changeSharp: int
    heroTempId: int
    userIds: _containers.RepeatedScalarFieldContainer[int]
    geste: int
    isVip: bool
    vipType: int
    mountTempId: int
    mountGrade: int
    wing: str
    serverName: str
    hat: str
    fashionArm: str
    fashionCloth: str
    hide: bool
    appellid: int
    fateSkills: str
    petTempId: int
    petQuqlity: int
    petName: str
    def __init__(self, armyId: _Optional[int] = ..., playerId: _Optional[int] = ..., nickName: _Optional[str] = ..., mapId: _Optional[int] = ..., curPosX: _Optional[int] = ..., curPosY: _Optional[int] = ..., state: _Optional[int] = ..., type: _Optional[int] = ..., armyPawn: _Optional[_Iterable[_Union[ArmyPawnInfoMsg, _Mapping]]] = ..., simpleHeroInfo: _Optional[_Union[SimpleHeroInfoMsg, _Mapping]] = ..., consortiaId: _Optional[int] = ..., consortiaName: _Optional[str] = ..., fightingCapacity: _Optional[int] = ..., gpOrder: _Optional[int] = ..., grades: _Optional[int] = ..., arm: _Optional[str] = ..., cloth: _Optional[str] = ..., job: _Optional[int] = ..., changeSharp: _Optional[int] = ..., heroTempId: _Optional[int] = ..., userIds: _Optional[_Iterable[int]] = ..., geste: _Optional[int] = ..., isVip: _Optional[bool] = ..., vipType: _Optional[int] = ..., mountTempId: _Optional[int] = ..., mountGrade: _Optional[int] = ..., wing: _Optional[str] = ..., serverName: _Optional[str] = ..., hat: _Optional[str] = ..., fashionArm: _Optional[str] = ..., fashionCloth: _Optional[str] = ..., hide: _Optional[bool] = ..., appellid: _Optional[int] = ..., fateSkills: _Optional[str] = ..., petTempId: _Optional[int] = ..., petQuqlity: _Optional[int] = ..., petName: _Optional[str] = ...) -> None: ...

class ArmyArmyUpdatedGridMsg(_message.Message):
    __slots__ = ("updatedArmy",)
    UPDATEDARMY_FIELD_NUMBER: _ClassVar[int]
    updatedArmy: _containers.RepeatedCompositeFieldContainer[ArmyArmyMsg]
    def __init__(self, updatedArmy: _Optional[_Iterable[_Union[ArmyArmyMsg, _Mapping]]] = ...) -> None: ...

class ArmyBoxMsg(_message.Message):
    __slots__ = ("boxId", "userId", "grade", "mapId", "x", "y", "type")
    BOXID_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    GRADE_FIELD_NUMBER: _ClassVar[int]
    MAPID_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    boxId: str
    userId: int
    grade: int
    mapId: int
    x: int
    y: int
    type: int
    def __init__(self, boxId: _Optional[str] = ..., userId: _Optional[int] = ..., grade: _Optional[int] = ..., mapId: _Optional[int] = ..., x: _Optional[int] = ..., y: _Optional[int] = ..., type: _Optional[int] = ...) -> None: ...

class ArmyBufferListMsg(_message.Message):
    __slots__ = ("armyBuffer",)
    ARMYBUFFER_FIELD_NUMBER: _ClassVar[int]
    armyBuffer: _containers.RepeatedCompositeFieldContainer[ArmyBufferMsg]
    def __init__(self, armyBuffer: _Optional[_Iterable[_Union[ArmyBufferMsg, _Mapping]]] = ...) -> None: ...

class ArmyBufferMsg(_message.Message):
    __slots__ = ("userId", "bufferTempId")
    USERID_FIELD_NUMBER: _ClassVar[int]
    BUFFERTEMPID_FIELD_NUMBER: _ClassVar[int]
    userId: int
    bufferTempId: int
    def __init__(self, userId: _Optional[int] = ..., bufferTempId: _Optional[int] = ...) -> None: ...

class ArmyChangeSharpMsg(_message.Message):
    __slots__ = ("armyId", "changeSharpId", "serverName")
    ARMYID_FIELD_NUMBER: _ClassVar[int]
    CHANGESHARPID_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    armyId: int
    changeSharpId: int
    serverName: str
    def __init__(self, armyId: _Optional[int] = ..., changeSharpId: _Optional[int] = ..., serverName: _Optional[str] = ...) -> None: ...

class ArmyEditRspMsg(_message.Message):
    __slots__ = ("armyPawn",)
    ARMYPAWN_FIELD_NUMBER: _ClassVar[int]
    armyPawn: _containers.RepeatedCompositeFieldContainer[ArmyPawnInfoMsg]
    def __init__(self, armyPawn: _Optional[_Iterable[_Union[ArmyPawnInfoMsg, _Mapping]]] = ...) -> None: ...

class ArmyFightPosEditListMsg(_message.Message):
    __slots__ = ("armyFightPos",)
    ARMYFIGHTPOS_FIELD_NUMBER: _ClassVar[int]
    armyFightPos: _containers.RepeatedCompositeFieldContainer[ArmyFightPosEditMsg]
    def __init__(self, armyFightPos: _Optional[_Iterable[_Union[ArmyFightPosEditMsg, _Mapping]]] = ...) -> None: ...

class ArmyFightPosEditMsg(_message.Message):
    __slots__ = ("userId", "heroPos", "pawnPos")
    USERID_FIELD_NUMBER: _ClassVar[int]
    HEROPOS_FIELD_NUMBER: _ClassVar[int]
    PAWNPOS_FIELD_NUMBER: _ClassVar[int]
    userId: int
    heroPos: int
    pawnPos: int
    def __init__(self, userId: _Optional[int] = ..., heroPos: _Optional[int] = ..., pawnPos: _Optional[int] = ...) -> None: ...

class ArmyListRspMsg(_message.Message):
    __slots__ = ("armyList",)
    ARMYLIST_FIELD_NUMBER: _ClassVar[int]
    armyList: _containers.RepeatedCompositeFieldContainer[ArmyArmyMsg]
    def __init__(self, armyList: _Optional[_Iterable[_Union[ArmyArmyMsg, _Mapping]]] = ...) -> None: ...

class ArmyPawnInfoMsg(_message.Message):
    __slots__ = ("id", "armyId", "sites", "sonType", "tempateId", "ownPawns", "pawnLive", "fightPos", "specialTempIds", "comprehednTempIds", "blessNum")
    ID_FIELD_NUMBER: _ClassVar[int]
    ARMYID_FIELD_NUMBER: _ClassVar[int]
    SITES_FIELD_NUMBER: _ClassVar[int]
    SONTYPE_FIELD_NUMBER: _ClassVar[int]
    TEMPATEID_FIELD_NUMBER: _ClassVar[int]
    OWNPAWNS_FIELD_NUMBER: _ClassVar[int]
    PAWNLIVE_FIELD_NUMBER: _ClassVar[int]
    FIGHTPOS_FIELD_NUMBER: _ClassVar[int]
    SPECIALTEMPIDS_FIELD_NUMBER: _ClassVar[int]
    COMPREHEDNTEMPIDS_FIELD_NUMBER: _ClassVar[int]
    BLESSNUM_FIELD_NUMBER: _ClassVar[int]
    id: int
    armyId: int
    sites: int
    sonType: int
    tempateId: int
    ownPawns: int
    pawnLive: _containers.RepeatedCompositeFieldContainer[ArmyPropertyMsg]
    fightPos: int
    specialTempIds: str
    comprehednTempIds: str
    blessNum: int
    def __init__(self, id: _Optional[int] = ..., armyId: _Optional[int] = ..., sites: _Optional[int] = ..., sonType: _Optional[int] = ..., tempateId: _Optional[int] = ..., ownPawns: _Optional[int] = ..., pawnLive: _Optional[_Iterable[_Union[ArmyPropertyMsg, _Mapping]]] = ..., fightPos: _Optional[int] = ..., specialTempIds: _Optional[str] = ..., comprehednTempIds: _Optional[str] = ..., blessNum: _Optional[int] = ...) -> None: ...

class ArmyPawnUpdatedMsg(_message.Message):
    __slots__ = ("armyPawn",)
    ARMYPAWN_FIELD_NUMBER: _ClassVar[int]
    armyPawn: _containers.RepeatedCompositeFieldContainer[ArmyPawnInfoMsg]
    def __init__(self, armyPawn: _Optional[_Iterable[_Union[ArmyPawnInfoMsg, _Mapping]]] = ...) -> None: ...

class ArmyPlayerInfoMsg(_message.Message):
    __slots__ = ("aasFactor", "isVip", "vipType", "gesteDecCount", "consortiaId", "consortiaName", "changeShapeId", "arm", "geste", "mountTempId", "mountGrade", "wing", "hat", "fashionArm", "fashionCloth", "hide", "isMaxCount", "vipGrade", "fateSkills", "petTempId")
    AASFACTOR_FIELD_NUMBER: _ClassVar[int]
    ISVIP_FIELD_NUMBER: _ClassVar[int]
    VIPTYPE_FIELD_NUMBER: _ClassVar[int]
    GESTEDECCOUNT_FIELD_NUMBER: _ClassVar[int]
    CONSORTIAID_FIELD_NUMBER: _ClassVar[int]
    CONSORTIANAME_FIELD_NUMBER: _ClassVar[int]
    CHANGESHAPEID_FIELD_NUMBER: _ClassVar[int]
    ARM_FIELD_NUMBER: _ClassVar[int]
    GESTE_FIELD_NUMBER: _ClassVar[int]
    MOUNTTEMPID_FIELD_NUMBER: _ClassVar[int]
    MOUNTGRADE_FIELD_NUMBER: _ClassVar[int]
    WING_FIELD_NUMBER: _ClassVar[int]
    HAT_FIELD_NUMBER: _ClassVar[int]
    FASHIONARM_FIELD_NUMBER: _ClassVar[int]
    FASHIONCLOTH_FIELD_NUMBER: _ClassVar[int]
    HIDE_FIELD_NUMBER: _ClassVar[int]
    ISMAXCOUNT_FIELD_NUMBER: _ClassVar[int]
    VIPGRADE_FIELD_NUMBER: _ClassVar[int]
    FATESKILLS_FIELD_NUMBER: _ClassVar[int]
    PETTEMPID_FIELD_NUMBER: _ClassVar[int]
    aasFactor: float
    isVip: bool
    vipType: int
    gesteDecCount: int
    consortiaId: int
    consortiaName: str
    changeShapeId: int
    arm: str
    geste: int
    mountTempId: int
    mountGrade: int
    wing: str
    hat: str
    fashionArm: str
    fashionCloth: str
    hide: bool
    isMaxCount: bool
    vipGrade: int
    fateSkills: str
    petTempId: int
    def __init__(self, aasFactor: _Optional[float] = ..., isVip: _Optional[bool] = ..., vipType: _Optional[int] = ..., gesteDecCount: _Optional[int] = ..., consortiaId: _Optional[int] = ..., consortiaName: _Optional[str] = ..., changeShapeId: _Optional[int] = ..., arm: _Optional[str] = ..., geste: _Optional[int] = ..., mountTempId: _Optional[int] = ..., mountGrade: _Optional[int] = ..., wing: _Optional[str] = ..., hat: _Optional[str] = ..., fashionArm: _Optional[str] = ..., fashionCloth: _Optional[str] = ..., hide: _Optional[bool] = ..., isMaxCount: _Optional[bool] = ..., vipGrade: _Optional[int] = ..., fateSkills: _Optional[str] = ..., petTempId: _Optional[int] = ...) -> None: ...

class ArmyPosUpdatedMsg(_message.Message):
    __slots__ = ("armyId", "curPosX", "curPosY", "endPosX", "endPosY", "userIds", "serverName")
    ARMYID_FIELD_NUMBER: _ClassVar[int]
    CURPOSX_FIELD_NUMBER: _ClassVar[int]
    CURPOSY_FIELD_NUMBER: _ClassVar[int]
    ENDPOSX_FIELD_NUMBER: _ClassVar[int]
    ENDPOSY_FIELD_NUMBER: _ClassVar[int]
    USERIDS_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    armyId: int
    curPosX: int
    curPosY: int
    endPosX: int
    endPosY: int
    userIds: _containers.RepeatedScalarFieldContainer[int]
    serverName: str
    def __init__(self, armyId: _Optional[int] = ..., curPosX: _Optional[int] = ..., curPosY: _Optional[int] = ..., endPosX: _Optional[int] = ..., endPosY: _Optional[int] = ..., userIds: _Optional[_Iterable[int]] = ..., serverName: _Optional[str] = ...) -> None: ...

class ArmyPositionMsg(_message.Message):
    __slots__ = ("posX", "posY", "mapId", "payType", "leftEnergy")
    POSX_FIELD_NUMBER: _ClassVar[int]
    POSY_FIELD_NUMBER: _ClassVar[int]
    MAPID_FIELD_NUMBER: _ClassVar[int]
    PAYTYPE_FIELD_NUMBER: _ClassVar[int]
    LEFTENERGY_FIELD_NUMBER: _ClassVar[int]
    posX: int
    posY: int
    mapId: int
    payType: int
    leftEnergy: int
    def __init__(self, posX: _Optional[int] = ..., posY: _Optional[int] = ..., mapId: _Optional[int] = ..., payType: _Optional[int] = ..., leftEnergy: _Optional[int] = ...) -> None: ...

class ArmyPropertyMsg(_message.Message):
    __slots__ = ("tempData", "effect_Per", "effect_Data", "bag_Per", "bag_Data", "star_Per", "star_Data", "powcard_Per", "powcard_Data", "skill_Per", "skill_Data", "base_Join")
    TEMPDATA_FIELD_NUMBER: _ClassVar[int]
    EFFECT_PER_FIELD_NUMBER: _ClassVar[int]
    EFFECT_DATA_FIELD_NUMBER: _ClassVar[int]
    BAG_PER_FIELD_NUMBER: _ClassVar[int]
    BAG_DATA_FIELD_NUMBER: _ClassVar[int]
    STAR_PER_FIELD_NUMBER: _ClassVar[int]
    STAR_DATA_FIELD_NUMBER: _ClassVar[int]
    POWCARD_PER_FIELD_NUMBER: _ClassVar[int]
    POWCARD_DATA_FIELD_NUMBER: _ClassVar[int]
    SKILL_PER_FIELD_NUMBER: _ClassVar[int]
    SKILL_DATA_FIELD_NUMBER: _ClassVar[int]
    BASE_JOIN_FIELD_NUMBER: _ClassVar[int]
    tempData: int
    effect_Per: int
    effect_Data: int
    bag_Per: int
    bag_Data: int
    star_Per: int
    star_Data: int
    powcard_Per: int
    powcard_Data: int
    skill_Per: int
    skill_Data: int
    base_Join: int
    def __init__(self, tempData: _Optional[int] = ..., effect_Per: _Optional[int] = ..., effect_Data: _Optional[int] = ..., bag_Per: _Optional[int] = ..., bag_Data: _Optional[int] = ..., star_Per: _Optional[int] = ..., star_Data: _Optional[int] = ..., powcard_Per: _Optional[int] = ..., powcard_Data: _Optional[int] = ..., skill_Per: _Optional[int] = ..., skill_Data: _Optional[int] = ..., base_Join: _Optional[int] = ...) -> None: ...

class ArmyRemoveMsg(_message.Message):
    __slots__ = ("armyId",)
    ARMYID_FIELD_NUMBER: _ClassVar[int]
    armyId: int
    def __init__(self, armyId: _Optional[int] = ...) -> None: ...

class ArmyResMsg(_message.Message):
    __slots__ = ("loadRes", "reinforceCount", "reinforceType")
    LOADRES_FIELD_NUMBER: _ClassVar[int]
    REINFORCECOUNT_FIELD_NUMBER: _ClassVar[int]
    REINFORCETYPE_FIELD_NUMBER: _ClassVar[int]
    loadRes: _containers.RepeatedCompositeFieldContainer[PreLoadResMsg]
    reinforceCount: int
    reinforceType: int
    def __init__(self, loadRes: _Optional[_Iterable[_Union[PreLoadResMsg, _Mapping]]] = ..., reinforceCount: _Optional[int] = ..., reinforceType: _Optional[int] = ...) -> None: ...

class ArrangeInfo(_message.Message):
    __slots__ = ("oldplace", "newplace")
    OLDPLACE_FIELD_NUMBER: _ClassVar[int]
    NEWPLACE_FIELD_NUMBER: _ClassVar[int]
    oldplace: int
    newplace: int
    def __init__(self, oldplace: _Optional[int] = ..., newplace: _Optional[int] = ...) -> None: ...

class ArrangeReq(_message.Message):
    __slots__ = ("isStackItem", "bagType", "arrangeInfo")
    ISSTACKITEM_FIELD_NUMBER: _ClassVar[int]
    BAGTYPE_FIELD_NUMBER: _ClassVar[int]
    ARRANGEINFO_FIELD_NUMBER: _ClassVar[int]
    isStackItem: bool
    bagType: int
    arrangeInfo: _containers.RepeatedCompositeFieldContainer[ArrangeInfo]
    def __init__(self, isStackItem: _Optional[bool] = ..., bagType: _Optional[int] = ..., arrangeInfo: _Optional[_Iterable[_Union[ArrangeInfo, _Mapping]]] = ...) -> None: ...

class ArriveAltarReqMsg(_message.Message):
    __slots__ = ("uuId", "nodeId")
    UUID_FIELD_NUMBER: _ClassVar[int]
    NODEID_FIELD_NUMBER: _ClassVar[int]
    uuId: str
    nodeId: int
    def __init__(self, uuId: _Optional[str] = ..., nodeId: _Optional[int] = ...) -> None: ...

class AttackModeMsg(_message.Message):
    __slots__ = ("userId", "battleId", "serverName", "armyId", "mode", "fmTurn", "heroSp")
    USERID_FIELD_NUMBER: _ClassVar[int]
    BATTLEID_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    ARMYID_FIELD_NUMBER: _ClassVar[int]
    MODE_FIELD_NUMBER: _ClassVar[int]
    FMTURN_FIELD_NUMBER: _ClassVar[int]
    HEROSP_FIELD_NUMBER: _ClassVar[int]
    userId: int
    battleId: str
    serverName: str
    armyId: int
    mode: int
    fmTurn: int
    heroSp: int
    def __init__(self, userId: _Optional[int] = ..., battleId: _Optional[str] = ..., serverName: _Optional[str] = ..., armyId: _Optional[int] = ..., mode: _Optional[int] = ..., fmTurn: _Optional[int] = ..., heroSp: _Optional[int] = ...) -> None: ...

class AttackOrderMsg(_message.Message):
    __slots__ = ("battleId", "frame", "orderId", "isPassive", "livingId", "sp", "spAdded", "damages", "execFrame", "frameNum", "attackMillis", "buffers", "awakenSoldiers", "attackOrderSeq", "cdTime", "awake", "awakeAdd", "waitRevives", "curturn")
    BATTLEID_FIELD_NUMBER: _ClassVar[int]
    FRAME_FIELD_NUMBER: _ClassVar[int]
    ORDERID_FIELD_NUMBER: _ClassVar[int]
    ISPASSIVE_FIELD_NUMBER: _ClassVar[int]
    LIVINGID_FIELD_NUMBER: _ClassVar[int]
    SP_FIELD_NUMBER: _ClassVar[int]
    SPADDED_FIELD_NUMBER: _ClassVar[int]
    DAMAGES_FIELD_NUMBER: _ClassVar[int]
    EXECFRAME_FIELD_NUMBER: _ClassVar[int]
    FRAMENUM_FIELD_NUMBER: _ClassVar[int]
    ATTACKMILLIS_FIELD_NUMBER: _ClassVar[int]
    BUFFERS_FIELD_NUMBER: _ClassVar[int]
    AWAKENSOLDIERS_FIELD_NUMBER: _ClassVar[int]
    ATTACKORDERSEQ_FIELD_NUMBER: _ClassVar[int]
    CDTIME_FIELD_NUMBER: _ClassVar[int]
    AWAKE_FIELD_NUMBER: _ClassVar[int]
    AWAKEADD_FIELD_NUMBER: _ClassVar[int]
    WAITREVIVES_FIELD_NUMBER: _ClassVar[int]
    CURTURN_FIELD_NUMBER: _ClassVar[int]
    battleId: str
    frame: int
    orderId: int
    isPassive: bool
    livingId: int
    sp: int
    spAdded: int
    damages: _containers.RepeatedCompositeFieldContainer[DamageMsg]
    execFrame: int
    frameNum: int
    attackMillis: str
    buffers: _containers.RepeatedCompositeFieldContainer[BufferMsg]
    awakenSoldiers: _containers.RepeatedCompositeFieldContainer[SoldierMsg]
    attackOrderSeq: int
    cdTime: int
    awake: int
    awakeAdd: int
    waitRevives: _containers.RepeatedCompositeFieldContainer[WaitReviveMsg]
    curturn: int
    def __init__(self, battleId: _Optional[str] = ..., frame: _Optional[int] = ..., orderId: _Optional[int] = ..., isPassive: _Optional[bool] = ..., livingId: _Optional[int] = ..., sp: _Optional[int] = ..., spAdded: _Optional[int] = ..., damages: _Optional[_Iterable[_Union[DamageMsg, _Mapping]]] = ..., execFrame: _Optional[int] = ..., frameNum: _Optional[int] = ..., attackMillis: _Optional[str] = ..., buffers: _Optional[_Iterable[_Union[BufferMsg, _Mapping]]] = ..., awakenSoldiers: _Optional[_Iterable[_Union[SoldierMsg, _Mapping]]] = ..., attackOrderSeq: _Optional[int] = ..., cdTime: _Optional[int] = ..., awake: _Optional[int] = ..., awakeAdd: _Optional[int] = ..., waitRevives: _Optional[_Iterable[_Union[WaitReviveMsg, _Mapping]]] = ..., curturn: _Optional[int] = ...) -> None: ...

class AuctionItemReqMsg(_message.Message):
    __slots__ = ("id", "point")
    ID_FIELD_NUMBER: _ClassVar[int]
    POINT_FIELD_NUMBER: _ClassVar[int]
    id: int
    point: int
    def __init__(self, id: _Optional[int] = ..., point: _Optional[int] = ...) -> None: ...

class AuctionItemRspMsg(_message.Message):
    __slots__ = ("result", "itemBuy")
    RESULT_FIELD_NUMBER: _ClassVar[int]
    ITEMBUY_FIELD_NUMBER: _ClassVar[int]
    result: int
    itemBuy: MallItemBuyMsg
    def __init__(self, result: _Optional[int] = ..., itemBuy: _Optional[_Union[MallItemBuyMsg, _Mapping]] = ...) -> None: ...

class AuctionItemsMsg(_message.Message):
    __slots__ = ("pageIdx", "pageCount", "itemBuy", "sellItem")
    PAGEIDX_FIELD_NUMBER: _ClassVar[int]
    PAGECOUNT_FIELD_NUMBER: _ClassVar[int]
    ITEMBUY_FIELD_NUMBER: _ClassVar[int]
    SELLITEM_FIELD_NUMBER: _ClassVar[int]
    pageIdx: int
    pageCount: int
    itemBuy: _containers.RepeatedCompositeFieldContainer[MallItemBuyMsg]
    sellItem: _containers.RepeatedCompositeFieldContainer[MallItemMsg]
    def __init__(self, pageIdx: _Optional[int] = ..., pageCount: _Optional[int] = ..., itemBuy: _Optional[_Iterable[_Union[MallItemBuyMsg, _Mapping]]] = ..., sellItem: _Optional[_Iterable[_Union[MallItemMsg, _Mapping]]] = ...) -> None: ...

class AvatarInfoMsg(_message.Message):
    __slots__ = ("mountTempId", "isExist", "expairDate", "activeDate", "validity", "starLevel", "blessing", "param1", "param2", "isBuyFly")
    MOUNTTEMPID_FIELD_NUMBER: _ClassVar[int]
    ISEXIST_FIELD_NUMBER: _ClassVar[int]
    EXPAIRDATE_FIELD_NUMBER: _ClassVar[int]
    ACTIVEDATE_FIELD_NUMBER: _ClassVar[int]
    VALIDITY_FIELD_NUMBER: _ClassVar[int]
    STARLEVEL_FIELD_NUMBER: _ClassVar[int]
    BLESSING_FIELD_NUMBER: _ClassVar[int]
    PARAM1_FIELD_NUMBER: _ClassVar[int]
    PARAM2_FIELD_NUMBER: _ClassVar[int]
    ISBUYFLY_FIELD_NUMBER: _ClassVar[int]
    mountTempId: int
    isExist: bool
    expairDate: str
    activeDate: str
    validity: int
    starLevel: int
    blessing: int
    param1: int
    param2: int
    isBuyFly: bool
    def __init__(self, mountTempId: _Optional[int] = ..., isExist: _Optional[bool] = ..., expairDate: _Optional[str] = ..., activeDate: _Optional[str] = ..., validity: _Optional[int] = ..., starLevel: _Optional[int] = ..., blessing: _Optional[int] = ..., param1: _Optional[int] = ..., param2: _Optional[int] = ..., isBuyFly: _Optional[bool] = ...) -> None: ...

class AvaterMsg(_message.Message):
    __slots__ = ("userId", "armTempId", "clothTempId", "fashionArmTempId", "fashionClothTempId", "fashionWingTempId", "fashionHeadTempId")
    USERID_FIELD_NUMBER: _ClassVar[int]
    ARMTEMPID_FIELD_NUMBER: _ClassVar[int]
    CLOTHTEMPID_FIELD_NUMBER: _ClassVar[int]
    FASHIONARMTEMPID_FIELD_NUMBER: _ClassVar[int]
    FASHIONCLOTHTEMPID_FIELD_NUMBER: _ClassVar[int]
    FASHIONWINGTEMPID_FIELD_NUMBER: _ClassVar[int]
    FASHIONHEADTEMPID_FIELD_NUMBER: _ClassVar[int]
    userId: int
    armTempId: int
    clothTempId: int
    fashionArmTempId: int
    fashionClothTempId: int
    fashionWingTempId: int
    fashionHeadTempId: int
    def __init__(self, userId: _Optional[int] = ..., armTempId: _Optional[int] = ..., clothTempId: _Optional[int] = ..., fashionArmTempId: _Optional[int] = ..., fashionClothTempId: _Optional[int] = ..., fashionWingTempId: _Optional[int] = ..., fashionHeadTempId: _Optional[int] = ...) -> None: ...

class AwakeInfoMsg(_message.Message):
    __slots__ = ("livingId", "awake")
    LIVINGID_FIELD_NUMBER: _ClassVar[int]
    AWAKE_FIELD_NUMBER: _ClassVar[int]
    livingId: int
    awake: int
    def __init__(self, livingId: _Optional[int] = ..., awake: _Optional[int] = ...) -> None: ...

class AwakeMsg(_message.Message):
    __slots__ = ("awake",)
    AWAKE_FIELD_NUMBER: _ClassVar[int]
    awake: _containers.RepeatedCompositeFieldContainer[AwakeInfoMsg]
    def __init__(self, awake: _Optional[_Iterable[_Union[AwakeInfoMsg, _Mapping]]] = ...) -> None: ...

class BaseCastleMsg(_message.Message):
    __slots__ = ("id", "mapId", "posX", "posY", "templateId", "type", "occupyPlayerId", "occupyPlayerName", "occupyLeagueName", "state", "defenceLefttime", "castleName", "leftEnergy", "grade", "isDefenceBuffer", "vipCastleView", "vipType")
    ID_FIELD_NUMBER: _ClassVar[int]
    MAPID_FIELD_NUMBER: _ClassVar[int]
    POSX_FIELD_NUMBER: _ClassVar[int]
    POSY_FIELD_NUMBER: _ClassVar[int]
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    OCCUPYPLAYERID_FIELD_NUMBER: _ClassVar[int]
    OCCUPYPLAYERNAME_FIELD_NUMBER: _ClassVar[int]
    OCCUPYLEAGUENAME_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    DEFENCELEFTTIME_FIELD_NUMBER: _ClassVar[int]
    CASTLENAME_FIELD_NUMBER: _ClassVar[int]
    LEFTENERGY_FIELD_NUMBER: _ClassVar[int]
    GRADE_FIELD_NUMBER: _ClassVar[int]
    ISDEFENCEBUFFER_FIELD_NUMBER: _ClassVar[int]
    VIPCASTLEVIEW_FIELD_NUMBER: _ClassVar[int]
    VIPTYPE_FIELD_NUMBER: _ClassVar[int]
    id: int
    mapId: int
    posX: int
    posY: int
    templateId: int
    type: int
    occupyPlayerId: int
    occupyPlayerName: str
    occupyLeagueName: str
    state: int
    defenceLefttime: int
    castleName: str
    leftEnergy: int
    grade: int
    isDefenceBuffer: bool
    vipCastleView: int
    vipType: int
    def __init__(self, id: _Optional[int] = ..., mapId: _Optional[int] = ..., posX: _Optional[int] = ..., posY: _Optional[int] = ..., templateId: _Optional[int] = ..., type: _Optional[int] = ..., occupyPlayerId: _Optional[int] = ..., occupyPlayerName: _Optional[str] = ..., occupyLeagueName: _Optional[str] = ..., state: _Optional[int] = ..., defenceLefttime: _Optional[int] = ..., castleName: _Optional[str] = ..., leftEnergy: _Optional[int] = ..., grade: _Optional[int] = ..., isDefenceBuffer: _Optional[bool] = ..., vipCastleView: _Optional[int] = ..., vipType: _Optional[int] = ...) -> None: ...

class BaseItemMsg(_message.Message):
    __slots__ = ("templateId", "count")
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    templateId: int
    count: int
    def __init__(self, templateId: _Optional[int] = ..., count: _Optional[int] = ...) -> None: ...

class BatterLastInfoMsg(_message.Message):
    __slots__ = ("count",)
    COUNT_FIELD_NUMBER: _ClassVar[int]
    count: int
    def __init__(self, count: _Optional[int] = ...) -> None: ...

class BattleArmyMsg(_message.Message):
    __slots__ = ("id", "userId", "name", "type", "side", "formation", "hero", "soldier", "result", "isJoin", "armyType", "isRobot", "failedCount", "serverName", "armyPlayerInfo", "curWave", "pet")
    ID_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    SIDE_FIELD_NUMBER: _ClassVar[int]
    FORMATION_FIELD_NUMBER: _ClassVar[int]
    HERO_FIELD_NUMBER: _ClassVar[int]
    SOLDIER_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    ISJOIN_FIELD_NUMBER: _ClassVar[int]
    ARMYTYPE_FIELD_NUMBER: _ClassVar[int]
    ISROBOT_FIELD_NUMBER: _ClassVar[int]
    FAILEDCOUNT_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    ARMYPLAYERINFO_FIELD_NUMBER: _ClassVar[int]
    CURWAVE_FIELD_NUMBER: _ClassVar[int]
    PET_FIELD_NUMBER: _ClassVar[int]
    id: int
    userId: int
    name: str
    type: int
    side: int
    formation: int
    hero: _containers.RepeatedCompositeFieldContainer[HeroMsg]
    soldier: _containers.RepeatedCompositeFieldContainer[SoldierMsg]
    result: int
    isJoin: bool
    armyType: int
    isRobot: bool
    failedCount: int
    serverName: str
    armyPlayerInfo: ArmyPlayerInfoMsg
    curWave: int
    pet: _containers.RepeatedCompositeFieldContainer[HeroMsg]
    def __init__(self, id: _Optional[int] = ..., userId: _Optional[int] = ..., name: _Optional[str] = ..., type: _Optional[int] = ..., side: _Optional[int] = ..., formation: _Optional[int] = ..., hero: _Optional[_Iterable[_Union[HeroMsg, _Mapping]]] = ..., soldier: _Optional[_Iterable[_Union[SoldierMsg, _Mapping]]] = ..., result: _Optional[int] = ..., isJoin: _Optional[bool] = ..., armyType: _Optional[int] = ..., isRobot: _Optional[bool] = ..., failedCount: _Optional[int] = ..., serverName: _Optional[str] = ..., armyPlayerInfo: _Optional[_Union[ArmyPlayerInfoMsg, _Mapping]] = ..., curWave: _Optional[int] = ..., pet: _Optional[_Iterable[_Union[HeroMsg, _Mapping]]] = ...) -> None: ...

class BattleCreateMsg(_message.Message):
    __slots__ = ("mapTempId", "proxyId", "type", "attackerNum", "userSide", "army", "reinforceCount", "campaignId", "capity", "lastWound", "nodeId", "castleRoomId", "serverName")
    MAPTEMPID_FIELD_NUMBER: _ClassVar[int]
    PROXYID_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    ATTACKERNUM_FIELD_NUMBER: _ClassVar[int]
    USERSIDE_FIELD_NUMBER: _ClassVar[int]
    ARMY_FIELD_NUMBER: _ClassVar[int]
    REINFORCECOUNT_FIELD_NUMBER: _ClassVar[int]
    CAMPAIGNID_FIELD_NUMBER: _ClassVar[int]
    CAPITY_FIELD_NUMBER: _ClassVar[int]
    LASTWOUND_FIELD_NUMBER: _ClassVar[int]
    NODEID_FIELD_NUMBER: _ClassVar[int]
    CASTLEROOMID_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    mapTempId: int
    proxyId: str
    type: int
    attackerNum: int
    userSide: int
    army: _containers.RepeatedCompositeFieldContainer[BattleArmyMsg]
    reinforceCount: int
    campaignId: int
    capity: int
    lastWound: int
    nodeId: int
    castleRoomId: int
    serverName: str
    def __init__(self, mapTempId: _Optional[int] = ..., proxyId: _Optional[str] = ..., type: _Optional[int] = ..., attackerNum: _Optional[int] = ..., userSide: _Optional[int] = ..., army: _Optional[_Iterable[_Union[BattleArmyMsg, _Mapping]]] = ..., reinforceCount: _Optional[int] = ..., campaignId: _Optional[int] = ..., capity: _Optional[int] = ..., lastWound: _Optional[int] = ..., nodeId: _Optional[int] = ..., castleRoomId: _Optional[int] = ..., serverName: _Optional[str] = ...) -> None: ...

class BattleItemMsg(_message.Message):
    __slots__ = ("userId", "battleId", "serverName", "uItemId", "count", "tempId", "bagPos", "skillTempId", "sonType")
    USERID_FIELD_NUMBER: _ClassVar[int]
    BATTLEID_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    UITEMID_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    TEMPID_FIELD_NUMBER: _ClassVar[int]
    BAGPOS_FIELD_NUMBER: _ClassVar[int]
    SKILLTEMPID_FIELD_NUMBER: _ClassVar[int]
    SONTYPE_FIELD_NUMBER: _ClassVar[int]
    userId: int
    battleId: str
    serverName: str
    uItemId: int
    count: int
    tempId: int
    bagPos: int
    skillTempId: int
    sonType: int
    def __init__(self, userId: _Optional[int] = ..., battleId: _Optional[str] = ..., serverName: _Optional[str] = ..., uItemId: _Optional[int] = ..., count: _Optional[int] = ..., tempId: _Optional[int] = ..., bagPos: _Optional[int] = ..., skillTempId: _Optional[int] = ..., sonType: _Optional[int] = ...) -> None: ...

class BattleNoticeMsg(_message.Message):
    __slots__ = ("battleId", "countDown", "damageImprove")
    BATTLEID_FIELD_NUMBER: _ClassVar[int]
    COUNTDOWN_FIELD_NUMBER: _ClassVar[int]
    DAMAGEIMPROVE_FIELD_NUMBER: _ClassVar[int]
    battleId: str
    countDown: int
    damageImprove: int
    def __init__(self, battleId: _Optional[str] = ..., countDown: _Optional[int] = ..., damageImprove: _Optional[int] = ...) -> None: ...

class BattlePrepareMsg(_message.Message):
    __slots__ = ("battleId", "battleType", "mapTempId", "needAnimation", "side", "hasAssault", "useWay", "attackModel", "reinforceCount", "currentReinforce", "battleCapity", "countDown", "damageImprove", "soldiers", "heros", "soldierTemplated", "coolDown", "currentWave", "pets")
    BATTLEID_FIELD_NUMBER: _ClassVar[int]
    BATTLETYPE_FIELD_NUMBER: _ClassVar[int]
    MAPTEMPID_FIELD_NUMBER: _ClassVar[int]
    NEEDANIMATION_FIELD_NUMBER: _ClassVar[int]
    SIDE_FIELD_NUMBER: _ClassVar[int]
    HASASSAULT_FIELD_NUMBER: _ClassVar[int]
    USEWAY_FIELD_NUMBER: _ClassVar[int]
    ATTACKMODEL_FIELD_NUMBER: _ClassVar[int]
    REINFORCECOUNT_FIELD_NUMBER: _ClassVar[int]
    CURRENTREINFORCE_FIELD_NUMBER: _ClassVar[int]
    BATTLECAPITY_FIELD_NUMBER: _ClassVar[int]
    COUNTDOWN_FIELD_NUMBER: _ClassVar[int]
    DAMAGEIMPROVE_FIELD_NUMBER: _ClassVar[int]
    SOLDIERS_FIELD_NUMBER: _ClassVar[int]
    HEROS_FIELD_NUMBER: _ClassVar[int]
    SOLDIERTEMPLATED_FIELD_NUMBER: _ClassVar[int]
    COOLDOWN_FIELD_NUMBER: _ClassVar[int]
    CURRENTWAVE_FIELD_NUMBER: _ClassVar[int]
    PETS_FIELD_NUMBER: _ClassVar[int]
    battleId: str
    battleType: int
    mapTempId: int
    needAnimation: bool
    side: int
    hasAssault: bool
    useWay: int
    attackModel: int
    reinforceCount: int
    currentReinforce: int
    battleCapity: int
    countDown: int
    damageImprove: int
    soldiers: _containers.RepeatedCompositeFieldContainer[SoldierMsg]
    heros: _containers.RepeatedCompositeFieldContainer[HeroMsg]
    soldierTemplated: _containers.RepeatedScalarFieldContainer[int]
    coolDown: _containers.RepeatedCompositeFieldContainer[CoolDownMsg]
    currentWave: int
    pets: _containers.RepeatedCompositeFieldContainer[HeroMsg]
    def __init__(self, battleId: _Optional[str] = ..., battleType: _Optional[int] = ..., mapTempId: _Optional[int] = ..., needAnimation: _Optional[bool] = ..., side: _Optional[int] = ..., hasAssault: _Optional[bool] = ..., useWay: _Optional[int] = ..., attackModel: _Optional[int] = ..., reinforceCount: _Optional[int] = ..., currentReinforce: _Optional[int] = ..., battleCapity: _Optional[int] = ..., countDown: _Optional[int] = ..., damageImprove: _Optional[int] = ..., soldiers: _Optional[_Iterable[_Union[SoldierMsg, _Mapping]]] = ..., heros: _Optional[_Iterable[_Union[HeroMsg, _Mapping]]] = ..., soldierTemplated: _Optional[_Iterable[int]] = ..., coolDown: _Optional[_Iterable[_Union[CoolDownMsg, _Mapping]]] = ..., currentWave: _Optional[int] = ..., pets: _Optional[_Iterable[_Union[HeroMsg, _Mapping]]] = ...) -> None: ...

class BattleReportMsg(_message.Message):
    __slots__ = ("battleResult", "strategyBonus", "gpBonus", "posX", "posY", "signId", "baseItem", "battleScene", "failCount", "goldBonus", "petGpBonus", "param1", "param2")
    BATTLERESULT_FIELD_NUMBER: _ClassVar[int]
    STRATEGYBONUS_FIELD_NUMBER: _ClassVar[int]
    GPBONUS_FIELD_NUMBER: _ClassVar[int]
    POSX_FIELD_NUMBER: _ClassVar[int]
    POSY_FIELD_NUMBER: _ClassVar[int]
    SIGNID_FIELD_NUMBER: _ClassVar[int]
    BASEITEM_FIELD_NUMBER: _ClassVar[int]
    BATTLESCENE_FIELD_NUMBER: _ClassVar[int]
    FAILCOUNT_FIELD_NUMBER: _ClassVar[int]
    GOLDBONUS_FIELD_NUMBER: _ClassVar[int]
    PETGPBONUS_FIELD_NUMBER: _ClassVar[int]
    PARAM1_FIELD_NUMBER: _ClassVar[int]
    PARAM2_FIELD_NUMBER: _ClassVar[int]
    battleResult: int
    strategyBonus: int
    gpBonus: int
    posX: int
    posY: int
    signId: str
    baseItem: _containers.RepeatedCompositeFieldContainer[BaseItemMsg]
    battleScene: int
    failCount: int
    goldBonus: int
    petGpBonus: int
    param1: int
    param2: int
    def __init__(self, battleResult: _Optional[int] = ..., strategyBonus: _Optional[int] = ..., gpBonus: _Optional[int] = ..., posX: _Optional[int] = ..., posY: _Optional[int] = ..., signId: _Optional[str] = ..., baseItem: _Optional[_Iterable[_Union[BaseItemMsg, _Mapping]]] = ..., battleScene: _Optional[int] = ..., failCount: _Optional[int] = ..., goldBonus: _Optional[int] = ..., petGpBonus: _Optional[int] = ..., param1: _Optional[int] = ..., param2: _Optional[int] = ...) -> None: ...

class BattleReqMsg(_message.Message):
    __slots__ = ("userId", "battleId", "armyId", "otherObj")
    USERID_FIELD_NUMBER: _ClassVar[int]
    BATTLEID_FIELD_NUMBER: _ClassVar[int]
    ARMYID_FIELD_NUMBER: _ClassVar[int]
    OTHEROBJ_FIELD_NUMBER: _ClassVar[int]
    userId: int
    battleId: str
    armyId: int
    otherObj: int
    def __init__(self, userId: _Optional[int] = ..., battleId: _Optional[str] = ..., armyId: _Optional[int] = ..., otherObj: _Optional[int] = ...) -> None: ...

class BattleStartMsg(_message.Message):
    __slots__ = ("frame", "mainType", "countDown")
    FRAME_FIELD_NUMBER: _ClassVar[int]
    MAINTYPE_FIELD_NUMBER: _ClassVar[int]
    COUNTDOWN_FIELD_NUMBER: _ClassVar[int]
    frame: int
    mainType: int
    countDown: int
    def __init__(self, frame: _Optional[int] = ..., mainType: _Optional[int] = ..., countDown: _Optional[int] = ...) -> None: ...

class BattleViewMsg(_message.Message):
    __slots__ = ("type", "userId", "serverName", "teamUuid", "sonType")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    TEAMUUID_FIELD_NUMBER: _ClassVar[int]
    SONTYPE_FIELD_NUMBER: _ClassVar[int]
    type: int
    userId: int
    serverName: str
    teamUuid: str
    sonType: int
    def __init__(self, type: _Optional[int] = ..., userId: _Optional[int] = ..., serverName: _Optional[str] = ..., teamUuid: _Optional[str] = ..., sonType: _Optional[int] = ...) -> None: ...

class BlessingMsg(_message.Message):
    __slots__ = ("increase", "usedCount", "maxCount")
    INCREASE_FIELD_NUMBER: _ClassVar[int]
    USEDCOUNT_FIELD_NUMBER: _ClassVar[int]
    MAXCOUNT_FIELD_NUMBER: _ClassVar[int]
    increase: int
    usedCount: int
    maxCount: int
    def __init__(self, increase: _Optional[int] = ..., usedCount: _Optional[int] = ..., maxCount: _Optional[int] = ...) -> None: ...

class BossArmyListMsg(_message.Message):
    __slots__ = ("leftFightTime", "bossName", "level", "bossTemplateId", "fightPlayer")
    LEFTFIGHTTIME_FIELD_NUMBER: _ClassVar[int]
    BOSSNAME_FIELD_NUMBER: _ClassVar[int]
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    BOSSTEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    FIGHTPLAYER_FIELD_NUMBER: _ClassVar[int]
    leftFightTime: int
    bossName: str
    level: int
    bossTemplateId: int
    fightPlayer: _containers.RepeatedCompositeFieldContainer[FightPlayerMsg]
    def __init__(self, leftFightTime: _Optional[int] = ..., bossName: _Optional[str] = ..., level: _Optional[int] = ..., bossTemplateId: _Optional[int] = ..., fightPlayer: _Optional[_Iterable[_Union[FightPlayerMsg, _Mapping]]] = ...) -> None: ...

class BossHpMsg(_message.Message):
    __slots__ = ("campaignId", "value", "nodeId", "livingId")
    CAMPAIGNID_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    NODEID_FIELD_NUMBER: _ClassVar[int]
    LIVINGID_FIELD_NUMBER: _ClassVar[int]
    campaignId: int
    value: int
    nodeId: int
    livingId: int
    def __init__(self, campaignId: _Optional[int] = ..., value: _Optional[int] = ..., nodeId: _Optional[int] = ..., livingId: _Optional[int] = ...) -> None: ...

class BossInviteMsg(_message.Message):
    __slots__ = ("nickName", "bossNick", "level", "templateId", "leftFightTime", "posX", "posY")
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    BOSSNICK_FIELD_NUMBER: _ClassVar[int]
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    LEFTFIGHTTIME_FIELD_NUMBER: _ClassVar[int]
    POSX_FIELD_NUMBER: _ClassVar[int]
    POSY_FIELD_NUMBER: _ClassVar[int]
    nickName: str
    bossNick: str
    level: int
    templateId: int
    leftFightTime: int
    posX: int
    posY: int
    def __init__(self, nickName: _Optional[str] = ..., bossNick: _Optional[str] = ..., level: _Optional[int] = ..., templateId: _Optional[int] = ..., leftFightTime: _Optional[int] = ..., posX: _Optional[int] = ..., posY: _Optional[int] = ...) -> None: ...

class BossMsg(_message.Message):
    __slots__ = ("bossName", "grade", "type", "x", "y")
    BOSSNAME_FIELD_NUMBER: _ClassVar[int]
    GRADE_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    bossName: str
    grade: int
    type: int
    x: int
    y: int
    def __init__(self, bossName: _Optional[str] = ..., grade: _Optional[int] = ..., type: _Optional[int] = ..., x: _Optional[int] = ..., y: _Optional[int] = ...) -> None: ...

class BottleDropListMsg(_message.Message):
    __slots__ = ("dropItem", "score", "storey", "open", "endTime")
    DROPITEM_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    STOREY_FIELD_NUMBER: _ClassVar[int]
    OPEN_FIELD_NUMBER: _ClassVar[int]
    ENDTIME_FIELD_NUMBER: _ClassVar[int]
    dropItem: _containers.RepeatedCompositeFieldContainer[BottleItemInfoMsg]
    score: _containers.RepeatedCompositeFieldContainer[BottlePackage]
    storey: _containers.RepeatedCompositeFieldContainer[BottlePackage]
    open: bool
    endTime: int
    def __init__(self, dropItem: _Optional[_Iterable[_Union[BottleItemInfoMsg, _Mapping]]] = ..., score: _Optional[_Iterable[_Union[BottlePackage, _Mapping]]] = ..., storey: _Optional[_Iterable[_Union[BottlePackage, _Mapping]]] = ..., open: _Optional[bool] = ..., endTime: _Optional[int] = ...) -> None: ...

class BottleItemInfoMsg(_message.Message):
    __slots__ = ("tempId", "count", "isShow", "isNewItems")
    TEMPID_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    ISSHOW_FIELD_NUMBER: _ClassVar[int]
    ISNEWITEMS_FIELD_NUMBER: _ClassVar[int]
    tempId: int
    count: int
    isShow: bool
    isNewItems: bool
    def __init__(self, tempId: _Optional[int] = ..., count: _Optional[int] = ..., isShow: _Optional[bool] = ..., isNewItems: _Optional[bool] = ...) -> None: ...

class BottleMsg(_message.Message):
    __slots__ = ("playerBottle", "total")
    PLAYERBOTTLE_FIELD_NUMBER: _ClassVar[int]
    TOTAL_FIELD_NUMBER: _ClassVar[int]
    playerBottle: _containers.RepeatedCompositeFieldContainer[PlayerBottleMsg]
    total: int
    def __init__(self, playerBottle: _Optional[_Iterable[_Union[PlayerBottleMsg, _Mapping]]] = ..., total: _Optional[int] = ...) -> None: ...

class BottleOpMsg(_message.Message):
    __slots__ = ("alterType", "opType", "stickFirst")
    ALTERTYPE_FIELD_NUMBER: _ClassVar[int]
    OPTYPE_FIELD_NUMBER: _ClassVar[int]
    STICKFIRST_FIELD_NUMBER: _ClassVar[int]
    alterType: int
    opType: int
    stickFirst: int
    def __init__(self, alterType: _Optional[int] = ..., opType: _Optional[int] = ..., stickFirst: _Optional[int] = ...) -> None: ...

class BottlePackage(_message.Message):
    __slots__ = ("param", "item")
    PARAM_FIELD_NUMBER: _ClassVar[int]
    ITEM_FIELD_NUMBER: _ClassVar[int]
    param: int
    item: _containers.RepeatedCompositeFieldContainer[BottleItemInfoMsg]
    def __init__(self, param: _Optional[int] = ..., item: _Optional[_Iterable[_Union[BottleItemInfoMsg, _Mapping]]] = ...) -> None: ...

class BottlePassMsg(_message.Message):
    __slots__ = ("passType", "infos", "count", "dropId")
    PASSTYPE_FIELD_NUMBER: _ClassVar[int]
    INFOS_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    DROPID_FIELD_NUMBER: _ClassVar[int]
    passType: int
    infos: _containers.RepeatedScalarFieldContainer[str]
    count: int
    dropId: int
    def __init__(self, passType: _Optional[int] = ..., infos: _Optional[_Iterable[str]] = ..., count: _Optional[int] = ..., dropId: _Optional[int] = ...) -> None: ...

class BottleScoreMsg(_message.Message):
    __slots__ = ("treeStatus", "count", "openView", "alterBottle")
    TREESTATUS_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    OPENVIEW_FIELD_NUMBER: _ClassVar[int]
    ALTERBOTTLE_FIELD_NUMBER: _ClassVar[int]
    treeStatus: str
    count: int
    openView: bool
    alterBottle: bool
    def __init__(self, treeStatus: _Optional[str] = ..., count: _Optional[int] = ..., openView: _Optional[bool] = ..., alterBottle: _Optional[bool] = ...) -> None: ...

class BoxBoxMsg(_message.Message):
    __slots__ = ("time", "grade", "operate", "timerun")
    TIME_FIELD_NUMBER: _ClassVar[int]
    GRADE_FIELD_NUMBER: _ClassVar[int]
    OPERATE_FIELD_NUMBER: _ClassVar[int]
    TIMERUN_FIELD_NUMBER: _ClassVar[int]
    time: int
    grade: int
    operate: bool
    timerun: int
    def __init__(self, time: _Optional[int] = ..., grade: _Optional[int] = ..., operate: _Optional[bool] = ..., timerun: _Optional[int] = ...) -> None: ...

class BufferDataMsg(_message.Message):
    __slots__ = ("templateId", "validityDate", "grade", "type", "typeTemplateid", "isCancel")
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    VALIDITYDATE_FIELD_NUMBER: _ClassVar[int]
    GRADE_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    TYPETEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    ISCANCEL_FIELD_NUMBER: _ClassVar[int]
    templateId: int
    validityDate: int
    grade: int
    type: int
    typeTemplateid: int
    isCancel: bool
    def __init__(self, templateId: _Optional[int] = ..., validityDate: _Optional[int] = ..., grade: _Optional[int] = ..., type: _Optional[int] = ..., typeTemplateid: _Optional[int] = ..., isCancel: _Optional[bool] = ...) -> None: ...

class BufferInfoMsg(_message.Message):
    __slots__ = ("bufferTempId", "leftTime")
    BUFFERTEMPID_FIELD_NUMBER: _ClassVar[int]
    LEFTTIME_FIELD_NUMBER: _ClassVar[int]
    bufferTempId: int
    leftTime: int
    def __init__(self, bufferTempId: _Optional[int] = ..., leftTime: _Optional[int] = ...) -> None: ...

class BufferMsg(_message.Message):
    __slots__ = ("bufferId", "templateId", "sourceId", "targetId", "curTurn", "execFrame", "seeType", "exeWay", "pressedNum", "damage", "maxTurn", "unSkillIds")
    BUFFERID_FIELD_NUMBER: _ClassVar[int]
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    SOURCEID_FIELD_NUMBER: _ClassVar[int]
    TARGETID_FIELD_NUMBER: _ClassVar[int]
    CURTURN_FIELD_NUMBER: _ClassVar[int]
    EXECFRAME_FIELD_NUMBER: _ClassVar[int]
    SEETYPE_FIELD_NUMBER: _ClassVar[int]
    EXEWAY_FIELD_NUMBER: _ClassVar[int]
    PRESSEDNUM_FIELD_NUMBER: _ClassVar[int]
    DAMAGE_FIELD_NUMBER: _ClassVar[int]
    MAXTURN_FIELD_NUMBER: _ClassVar[int]
    UNSKILLIDS_FIELD_NUMBER: _ClassVar[int]
    bufferId: int
    templateId: int
    sourceId: int
    targetId: int
    curTurn: int
    execFrame: int
    seeType: int
    exeWay: int
    pressedNum: int
    damage: _containers.RepeatedCompositeFieldContainer[DamageMsg]
    maxTurn: int
    unSkillIds: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, bufferId: _Optional[int] = ..., templateId: _Optional[int] = ..., sourceId: _Optional[int] = ..., targetId: _Optional[int] = ..., curTurn: _Optional[int] = ..., execFrame: _Optional[int] = ..., seeType: _Optional[int] = ..., exeWay: _Optional[int] = ..., pressedNum: _Optional[int] = ..., damage: _Optional[_Iterable[_Union[DamageMsg, _Mapping]]] = ..., maxTurn: _Optional[int] = ..., unSkillIds: _Optional[_Iterable[int]] = ...) -> None: ...

class BuildOrderList(_message.Message):
    __slots__ = ("buildOrder",)
    BUILDORDER_FIELD_NUMBER: _ClassVar[int]
    buildOrder: _containers.RepeatedCompositeFieldContainer[OrderInfoMsg]
    def __init__(self, buildOrder: _Optional[_Iterable[_Union[OrderInfoMsg, _Mapping]]] = ...) -> None: ...

class BuildingInfoListMsg(_message.Message):
    __slots__ = ("result", "building")
    RESULT_FIELD_NUMBER: _ClassVar[int]
    BUILDING_FIELD_NUMBER: _ClassVar[int]
    result: bool
    building: _containers.RepeatedCompositeFieldContainer[BuildingInfoMsg]
    def __init__(self, result: _Optional[bool] = ..., building: _Optional[_Iterable[_Union[BuildingInfoMsg, _Mapping]]] = ...) -> None: ...

class BuildingInfoMsg(_message.Message):
    __slots__ = ("userId", "buildingId", "castleId", "createdDate", "isExist", "templateId", "sonType", "propterty1", "propterty2")
    USERID_FIELD_NUMBER: _ClassVar[int]
    BUILDINGID_FIELD_NUMBER: _ClassVar[int]
    CASTLEID_FIELD_NUMBER: _ClassVar[int]
    CREATEDDATE_FIELD_NUMBER: _ClassVar[int]
    ISEXIST_FIELD_NUMBER: _ClassVar[int]
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    SONTYPE_FIELD_NUMBER: _ClassVar[int]
    PROPTERTY1_FIELD_NUMBER: _ClassVar[int]
    PROPTERTY2_FIELD_NUMBER: _ClassVar[int]
    userId: int
    buildingId: int
    castleId: int
    createdDate: str
    isExist: bool
    templateId: int
    sonType: int
    propterty1: int
    propterty2: int
    def __init__(self, userId: _Optional[int] = ..., buildingId: _Optional[int] = ..., castleId: _Optional[int] = ..., createdDate: _Optional[str] = ..., isExist: _Optional[bool] = ..., templateId: _Optional[int] = ..., sonType: _Optional[int] = ..., propterty1: _Optional[int] = ..., propterty2: _Optional[int] = ...) -> None: ...

class BuildingOptionReqMsg(_message.Message):
    __slots__ = ("buildingId", "sonType")
    BUILDINGID_FIELD_NUMBER: _ClassVar[int]
    SONTYPE_FIELD_NUMBER: _ClassVar[int]
    buildingId: int
    sonType: int
    def __init__(self, buildingId: _Optional[int] = ..., sonType: _Optional[int] = ...) -> None: ...

class BuildingReqMsg(_message.Message):
    __slots__ = ("orderId", "position", "index", "userId")
    ORDERID_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    INDEX_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    orderId: int
    position: str
    index: int
    userId: int
    def __init__(self, orderId: _Optional[int] = ..., position: _Optional[str] = ..., index: _Optional[int] = ..., userId: _Optional[int] = ...) -> None: ...

class BuyInfo(_message.Message):
    __slots__ = ("isDiscount", "goodId", "count", "receiveId", "result", "type")
    ISDISCOUNT_FIELD_NUMBER: _ClassVar[int]
    GOODID_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    RECEIVEID_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    isDiscount: bool
    goodId: int
    count: int
    receiveId: int
    result: int
    type: int
    def __init__(self, isDiscount: _Optional[bool] = ..., goodId: _Optional[int] = ..., count: _Optional[int] = ..., receiveId: _Optional[int] = ..., result: _Optional[int] = ..., type: _Optional[int] = ...) -> None: ...

class CallBackReqMsg(_message.Message):
    __slots__ = ("mapId", "nodeId", "cmd")
    MAPID_FIELD_NUMBER: _ClassVar[int]
    NODEID_FIELD_NUMBER: _ClassVar[int]
    CMD_FIELD_NUMBER: _ClassVar[int]
    mapId: int
    nodeId: int
    cmd: int
    def __init__(self, mapId: _Optional[int] = ..., nodeId: _Optional[int] = ..., cmd: _Optional[int] = ...) -> None: ...

class CampaignBufferMsg(_message.Message):
    __slots__ = ("armyId", "bufferInfo", "property1", "property2", "property3")
    ARMYID_FIELD_NUMBER: _ClassVar[int]
    BUFFERINFO_FIELD_NUMBER: _ClassVar[int]
    PROPERTY1_FIELD_NUMBER: _ClassVar[int]
    PROPERTY2_FIELD_NUMBER: _ClassVar[int]
    PROPERTY3_FIELD_NUMBER: _ClassVar[int]
    armyId: int
    bufferInfo: _containers.RepeatedCompositeFieldContainer[BufferInfoMsg]
    property1: int
    property2: int
    property3: int
    def __init__(self, armyId: _Optional[int] = ..., bufferInfo: _Optional[_Iterable[_Union[BufferInfoMsg, _Mapping]]] = ..., property1: _Optional[int] = ..., property2: _Optional[int] = ..., property3: _Optional[int] = ...) -> None: ...

class CampaignCardsMsg(_message.Message):
    __slots__ = ("sceneType", "cardCount", "payCardCount", "price", "dropItems")
    SCENETYPE_FIELD_NUMBER: _ClassVar[int]
    CARDCOUNT_FIELD_NUMBER: _ClassVar[int]
    PAYCARDCOUNT_FIELD_NUMBER: _ClassVar[int]
    PRICE_FIELD_NUMBER: _ClassVar[int]
    DROPITEMS_FIELD_NUMBER: _ClassVar[int]
    sceneType: str
    cardCount: int
    payCardCount: int
    price: int
    dropItems: _containers.RepeatedCompositeFieldContainer[ItemInfoMsg]
    def __init__(self, sceneType: _Optional[str] = ..., cardCount: _Optional[int] = ..., payCardCount: _Optional[int] = ..., price: _Optional[int] = ..., dropItems: _Optional[_Iterable[_Union[ItemInfoMsg, _Mapping]]] = ...) -> None: ...

class CampaignConfirmMsg(_message.Message):
    __slots__ = ("title", "body", "mapId", "nodeId", "itemTempId", "itemCount", "type")
    TITLE_FIELD_NUMBER: _ClassVar[int]
    BODY_FIELD_NUMBER: _ClassVar[int]
    MAPID_FIELD_NUMBER: _ClassVar[int]
    NODEID_FIELD_NUMBER: _ClassVar[int]
    ITEMTEMPID_FIELD_NUMBER: _ClassVar[int]
    ITEMCOUNT_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    title: str
    body: str
    mapId: int
    nodeId: int
    itemTempId: int
    itemCount: int
    type: int
    def __init__(self, title: _Optional[str] = ..., body: _Optional[str] = ..., mapId: _Optional[int] = ..., nodeId: _Optional[int] = ..., itemTempId: _Optional[int] = ..., itemCount: _Optional[int] = ..., type: _Optional[int] = ...) -> None: ...

class CampaignExitMsg(_message.Message):
    __slots__ = ("result", "playerId", "armyId", "serverName")
    RESULT_FIELD_NUMBER: _ClassVar[int]
    PLAYERID_FIELD_NUMBER: _ClassVar[int]
    ARMYID_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    result: int
    playerId: int
    armyId: int
    serverName: str
    def __init__(self, result: _Optional[int] = ..., playerId: _Optional[int] = ..., armyId: _Optional[int] = ..., serverName: _Optional[str] = ...) -> None: ...

class CampaignFogDataListReqMsg(_message.Message):
    __slots__ = ("dataList",)
    DATALIST_FIELD_NUMBER: _ClassVar[int]
    dataList: _containers.RepeatedCompositeFieldContainer[CampaignFogDataReqMsg]
    def __init__(self, dataList: _Optional[_Iterable[_Union[CampaignFogDataReqMsg, _Mapping]]] = ...) -> None: ...

class CampaignFogDataReqMsg(_message.Message):
    __slots__ = ("index", "fogByte")
    INDEX_FIELD_NUMBER: _ClassVar[int]
    FOGBYTE_FIELD_NUMBER: _ClassVar[int]
    index: int
    fogByte: int
    def __init__(self, index: _Optional[int] = ..., fogByte: _Optional[int] = ...) -> None: ...

class CampaignFogMsg(_message.Message):
    __slots__ = ("row", "col", "forArray", "mapTempId")
    ROW_FIELD_NUMBER: _ClassVar[int]
    COL_FIELD_NUMBER: _ClassVar[int]
    FORARRAY_FIELD_NUMBER: _ClassVar[int]
    MAPTEMPID_FIELD_NUMBER: _ClassVar[int]
    row: int
    col: int
    forArray: _containers.RepeatedScalarFieldContainer[bytes]
    mapTempId: int
    def __init__(self, row: _Optional[int] = ..., col: _Optional[int] = ..., forArray: _Optional[_Iterable[bytes]] = ..., mapTempId: _Optional[int] = ...) -> None: ...

class CampaignFogUpdateMsg(_message.Message):
    __slots__ = ("fogUpdate",)
    FOGUPDATE_FIELD_NUMBER: _ClassVar[int]
    fogUpdate: _containers.RepeatedCompositeFieldContainer[FogUpdateMsg]
    def __init__(self, fogUpdate: _Optional[_Iterable[_Union[FogUpdateMsg, _Mapping]]] = ...) -> None: ...

class CampaignLoginMsg(_message.Message):
    __slots__ = ("playerId", "serverName")
    PLAYERID_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    playerId: int
    serverName: str
    def __init__(self, playerId: _Optional[int] = ..., serverName: _Optional[str] = ...) -> None: ...

class CampaignNodeListMsg(_message.Message):
    __slots__ = ("node",)
    NODE_FIELD_NUMBER: _ClassVar[int]
    node: _containers.RepeatedCompositeFieldContainer[CampaignNodeMsg]
    def __init__(self, node: _Optional[_Iterable[_Union[CampaignNodeMsg, _Mapping]]] = ...) -> None: ...

class CampaignNodeMsg(_message.Message):
    __slots__ = ("nodeId", "campDataId", "nodeName", "masterType", "sonType", "preNodeIds", "nextNodeIds", "state", "refreshSpeed", "posX", "posY", "curX", "curY", "level", "styleType", "attackTypes", "nameColor", "sizeType", "toward", "resource", "resetX", "resetY", "visitUserIds", "fixType", "fixX", "fixY", "heroTempId", "handlerRange", "fightCapaity", "param1", "param2", "param3", "param4", "param5")
    NODEID_FIELD_NUMBER: _ClassVar[int]
    CAMPDATAID_FIELD_NUMBER: _ClassVar[int]
    NODENAME_FIELD_NUMBER: _ClassVar[int]
    MASTERTYPE_FIELD_NUMBER: _ClassVar[int]
    SONTYPE_FIELD_NUMBER: _ClassVar[int]
    PRENODEIDS_FIELD_NUMBER: _ClassVar[int]
    NEXTNODEIDS_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    REFRESHSPEED_FIELD_NUMBER: _ClassVar[int]
    POSX_FIELD_NUMBER: _ClassVar[int]
    POSY_FIELD_NUMBER: _ClassVar[int]
    CURX_FIELD_NUMBER: _ClassVar[int]
    CURY_FIELD_NUMBER: _ClassVar[int]
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    STYLETYPE_FIELD_NUMBER: _ClassVar[int]
    ATTACKTYPES_FIELD_NUMBER: _ClassVar[int]
    NAMECOLOR_FIELD_NUMBER: _ClassVar[int]
    SIZETYPE_FIELD_NUMBER: _ClassVar[int]
    TOWARD_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_FIELD_NUMBER: _ClassVar[int]
    RESETX_FIELD_NUMBER: _ClassVar[int]
    RESETY_FIELD_NUMBER: _ClassVar[int]
    VISITUSERIDS_FIELD_NUMBER: _ClassVar[int]
    FIXTYPE_FIELD_NUMBER: _ClassVar[int]
    FIXX_FIELD_NUMBER: _ClassVar[int]
    FIXY_FIELD_NUMBER: _ClassVar[int]
    HEROTEMPID_FIELD_NUMBER: _ClassVar[int]
    HANDLERRANGE_FIELD_NUMBER: _ClassVar[int]
    FIGHTCAPAITY_FIELD_NUMBER: _ClassVar[int]
    PARAM1_FIELD_NUMBER: _ClassVar[int]
    PARAM2_FIELD_NUMBER: _ClassVar[int]
    PARAM3_FIELD_NUMBER: _ClassVar[int]
    PARAM4_FIELD_NUMBER: _ClassVar[int]
    PARAM5_FIELD_NUMBER: _ClassVar[int]
    nodeId: int
    campDataId: int
    nodeName: str
    masterType: int
    sonType: int
    preNodeIds: str
    nextNodeIds: str
    state: int
    refreshSpeed: int
    posX: int
    posY: int
    curX: int
    curY: int
    level: int
    styleType: int
    attackTypes: int
    nameColor: int
    sizeType: int
    toward: int
    resource: int
    resetX: int
    resetY: int
    visitUserIds: _containers.RepeatedScalarFieldContainer[int]
    fixType: int
    fixX: int
    fixY: int
    heroTempId: int
    handlerRange: int
    fightCapaity: int
    param1: int
    param2: int
    param3: str
    param4: str
    param5: str
    def __init__(self, nodeId: _Optional[int] = ..., campDataId: _Optional[int] = ..., nodeName: _Optional[str] = ..., masterType: _Optional[int] = ..., sonType: _Optional[int] = ..., preNodeIds: _Optional[str] = ..., nextNodeIds: _Optional[str] = ..., state: _Optional[int] = ..., refreshSpeed: _Optional[int] = ..., posX: _Optional[int] = ..., posY: _Optional[int] = ..., curX: _Optional[int] = ..., curY: _Optional[int] = ..., level: _Optional[int] = ..., styleType: _Optional[int] = ..., attackTypes: _Optional[int] = ..., nameColor: _Optional[int] = ..., sizeType: _Optional[int] = ..., toward: _Optional[int] = ..., resource: _Optional[int] = ..., resetX: _Optional[int] = ..., resetY: _Optional[int] = ..., visitUserIds: _Optional[_Iterable[int]] = ..., fixType: _Optional[int] = ..., fixX: _Optional[int] = ..., fixY: _Optional[int] = ..., heroTempId: _Optional[int] = ..., handlerRange: _Optional[int] = ..., fightCapaity: _Optional[int] = ..., param1: _Optional[int] = ..., param2: _Optional[int] = ..., param3: _Optional[str] = ..., param4: _Optional[str] = ..., param5: _Optional[str] = ...) -> None: ...

class CampaignNodePosRefershListMsg(_message.Message):
    __slots__ = ("node",)
    NODE_FIELD_NUMBER: _ClassVar[int]
    node: _containers.RepeatedCompositeFieldContainer[CampaignNodePosRefershMsg]
    def __init__(self, node: _Optional[_Iterable[_Union[CampaignNodePosRefershMsg, _Mapping]]] = ...) -> None: ...

class CampaignNodePosRefershMsg(_message.Message):
    __slots__ = ("mapId", "nodeId", "posX", "posY", "state")
    MAPID_FIELD_NUMBER: _ClassVar[int]
    NODEID_FIELD_NUMBER: _ClassVar[int]
    POSX_FIELD_NUMBER: _ClassVar[int]
    POSY_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    mapId: int
    nodeId: int
    posX: int
    posY: int
    state: int
    def __init__(self, mapId: _Optional[int] = ..., nodeId: _Optional[int] = ..., posX: _Optional[int] = ..., posY: _Optional[int] = ..., state: _Optional[int] = ...) -> None: ...

class CampaignNodeSuccMsg(_message.Message):
    __slots__ = ("nodeId",)
    NODEID_FIELD_NUMBER: _ClassVar[int]
    nodeId: int
    def __init__(self, nodeId: _Optional[int] = ...) -> None: ...

class CampaignNodeUpdateMsg(_message.Message):
    __slots__ = ("nodeId", "nodeState", "userId", "visitUserIds", "userIds", "uuId", "param1", "sonType", "posX", "posY", "param2", "param3")
    NODEID_FIELD_NUMBER: _ClassVar[int]
    NODESTATE_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    VISITUSERIDS_FIELD_NUMBER: _ClassVar[int]
    USERIDS_FIELD_NUMBER: _ClassVar[int]
    UUID_FIELD_NUMBER: _ClassVar[int]
    PARAM1_FIELD_NUMBER: _ClassVar[int]
    SONTYPE_FIELD_NUMBER: _ClassVar[int]
    POSX_FIELD_NUMBER: _ClassVar[int]
    POSY_FIELD_NUMBER: _ClassVar[int]
    PARAM2_FIELD_NUMBER: _ClassVar[int]
    PARAM3_FIELD_NUMBER: _ClassVar[int]
    nodeId: int
    nodeState: int
    userId: int
    visitUserIds: _containers.RepeatedScalarFieldContainer[int]
    userIds: _containers.RepeatedScalarFieldContainer[int]
    uuId: str
    param1: int
    sonType: int
    posX: int
    posY: int
    param2: int
    param3: int
    def __init__(self, nodeId: _Optional[int] = ..., nodeState: _Optional[int] = ..., userId: _Optional[int] = ..., visitUserIds: _Optional[_Iterable[int]] = ..., userIds: _Optional[_Iterable[int]] = ..., uuId: _Optional[str] = ..., param1: _Optional[int] = ..., sonType: _Optional[int] = ..., posX: _Optional[int] = ..., posY: _Optional[int] = ..., param2: _Optional[int] = ..., param3: _Optional[int] = ...) -> None: ...

class CampaignNotifyMsg(_message.Message):
    __slots__ = ("id", "scene", "mapId", "body", "delay")
    ID_FIELD_NUMBER: _ClassVar[int]
    SCENE_FIELD_NUMBER: _ClassVar[int]
    MAPID_FIELD_NUMBER: _ClassVar[int]
    BODY_FIELD_NUMBER: _ClassVar[int]
    DELAY_FIELD_NUMBER: _ClassVar[int]
    id: int
    scene: str
    mapId: int
    body: str
    delay: int
    def __init__(self, id: _Optional[int] = ..., scene: _Optional[str] = ..., mapId: _Optional[int] = ..., body: _Optional[str] = ..., delay: _Optional[int] = ...) -> None: ...

class CampaignNpcMoveListMsg(_message.Message):
    __slots__ = ("campaignNpcMove",)
    CAMPAIGNNPCMOVE_FIELD_NUMBER: _ClassVar[int]
    campaignNpcMove: _containers.RepeatedCompositeFieldContainer[CampaignNpcMoveMsg]
    def __init__(self, campaignNpcMove: _Optional[_Iterable[_Union[CampaignNpcMoveMsg, _Mapping]]] = ...) -> None: ...

class CampaignNpcMoveMsg(_message.Message):
    __slots__ = ("nodeId", "startX", "startY", "endX", "endY", "showTime", "uuId", "centerX", "centerY", "isMove")
    NODEID_FIELD_NUMBER: _ClassVar[int]
    STARTX_FIELD_NUMBER: _ClassVar[int]
    STARTY_FIELD_NUMBER: _ClassVar[int]
    ENDX_FIELD_NUMBER: _ClassVar[int]
    ENDY_FIELD_NUMBER: _ClassVar[int]
    SHOWTIME_FIELD_NUMBER: _ClassVar[int]
    UUID_FIELD_NUMBER: _ClassVar[int]
    CENTERX_FIELD_NUMBER: _ClassVar[int]
    CENTERY_FIELD_NUMBER: _ClassVar[int]
    ISMOVE_FIELD_NUMBER: _ClassVar[int]
    nodeId: int
    startX: int
    startY: int
    endX: int
    endY: int
    showTime: str
    uuId: str
    centerX: int
    centerY: int
    isMove: bool
    def __init__(self, nodeId: _Optional[int] = ..., startX: _Optional[int] = ..., startY: _Optional[int] = ..., endX: _Optional[int] = ..., endY: _Optional[int] = ..., showTime: _Optional[str] = ..., uuId: _Optional[str] = ..., centerX: _Optional[int] = ..., centerY: _Optional[int] = ..., isMove: _Optional[bool] = ...) -> None: ...

class CampaignReportMsg(_message.Message):
    __slots__ = ("time", "woundValue", "hurtValue", "failedCount", "woundAppraisal", "hurtAppraisal", "failedAppraisal", "totalAppraisal", "batter", "teamJoin", "friendJoin", "vipJoin", "propJoin", "otherJoin", "totalGp", "petGp")
    TIME_FIELD_NUMBER: _ClassVar[int]
    WOUNDVALUE_FIELD_NUMBER: _ClassVar[int]
    HURTVALUE_FIELD_NUMBER: _ClassVar[int]
    FAILEDCOUNT_FIELD_NUMBER: _ClassVar[int]
    WOUNDAPPRAISAL_FIELD_NUMBER: _ClassVar[int]
    HURTAPPRAISAL_FIELD_NUMBER: _ClassVar[int]
    FAILEDAPPRAISAL_FIELD_NUMBER: _ClassVar[int]
    TOTALAPPRAISAL_FIELD_NUMBER: _ClassVar[int]
    BATTER_FIELD_NUMBER: _ClassVar[int]
    TEAMJOIN_FIELD_NUMBER: _ClassVar[int]
    FRIENDJOIN_FIELD_NUMBER: _ClassVar[int]
    VIPJOIN_FIELD_NUMBER: _ClassVar[int]
    PROPJOIN_FIELD_NUMBER: _ClassVar[int]
    OTHERJOIN_FIELD_NUMBER: _ClassVar[int]
    TOTALGP_FIELD_NUMBER: _ClassVar[int]
    PETGP_FIELD_NUMBER: _ClassVar[int]
    time: int
    woundValue: int
    hurtValue: int
    failedCount: int
    woundAppraisal: int
    hurtAppraisal: int
    failedAppraisal: int
    totalAppraisal: int
    batter: int
    teamJoin: int
    friendJoin: int
    vipJoin: int
    propJoin: int
    otherJoin: int
    totalGp: int
    petGp: int
    def __init__(self, time: _Optional[int] = ..., woundValue: _Optional[int] = ..., hurtValue: _Optional[int] = ..., failedCount: _Optional[int] = ..., woundAppraisal: _Optional[int] = ..., hurtAppraisal: _Optional[int] = ..., failedAppraisal: _Optional[int] = ..., totalAppraisal: _Optional[int] = ..., batter: _Optional[int] = ..., teamJoin: _Optional[int] = ..., friendJoin: _Optional[int] = ..., vipJoin: _Optional[int] = ..., propJoin: _Optional[int] = ..., otherJoin: _Optional[int] = ..., totalGp: _Optional[int] = ..., petGp: _Optional[int] = ...) -> None: ...

class CampaignReqMsg(_message.Message):
    __slots__ = ("paraInt1", "paraInt2", "paraInt3", "paraInt4", "paraInt5", "paraString1", "paraBool1", "serverName")
    PARAINT1_FIELD_NUMBER: _ClassVar[int]
    PARAINT2_FIELD_NUMBER: _ClassVar[int]
    PARAINT3_FIELD_NUMBER: _ClassVar[int]
    PARAINT4_FIELD_NUMBER: _ClassVar[int]
    PARAINT5_FIELD_NUMBER: _ClassVar[int]
    PARASTRING1_FIELD_NUMBER: _ClassVar[int]
    PARABOOL1_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    paraInt1: int
    paraInt2: int
    paraInt3: int
    paraInt4: int
    paraInt5: int
    paraString1: str
    paraBool1: bool
    serverName: str
    def __init__(self, paraInt1: _Optional[int] = ..., paraInt2: _Optional[int] = ..., paraInt3: _Optional[int] = ..., paraInt4: _Optional[int] = ..., paraInt5: _Optional[int] = ..., paraString1: _Optional[str] = ..., paraBool1: _Optional[bool] = ..., serverName: _Optional[str] = ...) -> None: ...

class CampaignSweepReq(_message.Message):
    __slots__ = ("sweepType", "opType", "campaignId", "count", "eIndex", "enterType", "openSilverBox", "openSecretBox", "payType")
    SWEEPTYPE_FIELD_NUMBER: _ClassVar[int]
    OPTYPE_FIELD_NUMBER: _ClassVar[int]
    CAMPAIGNID_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    EINDEX_FIELD_NUMBER: _ClassVar[int]
    ENTERTYPE_FIELD_NUMBER: _ClassVar[int]
    OPENSILVERBOX_FIELD_NUMBER: _ClassVar[int]
    OPENSECRETBOX_FIELD_NUMBER: _ClassVar[int]
    PAYTYPE_FIELD_NUMBER: _ClassVar[int]
    sweepType: int
    opType: int
    campaignId: int
    count: int
    eIndex: int
    enterType: int
    openSilverBox: bool
    openSecretBox: bool
    payType: int
    def __init__(self, sweepType: _Optional[int] = ..., opType: _Optional[int] = ..., campaignId: _Optional[int] = ..., count: _Optional[int] = ..., eIndex: _Optional[int] = ..., enterType: _Optional[int] = ..., openSilverBox: _Optional[bool] = ..., openSecretBox: _Optional[bool] = ..., payType: _Optional[int] = ...) -> None: ...

class CampaignSweepRsp(_message.Message):
    __slots__ = ("result", "status", "sweepType", "totalGp", "dropItems", "campaignId")
    RESULT_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    SWEEPTYPE_FIELD_NUMBER: _ClassVar[int]
    TOTALGP_FIELD_NUMBER: _ClassVar[int]
    DROPITEMS_FIELD_NUMBER: _ClassVar[int]
    CAMPAIGNID_FIELD_NUMBER: _ClassVar[int]
    result: _containers.RepeatedCompositeFieldContainer[SweepResult]
    status: int
    sweepType: int
    totalGp: int
    dropItems: _containers.RepeatedCompositeFieldContainer[ItemTemplate]
    campaignId: int
    def __init__(self, result: _Optional[_Iterable[_Union[SweepResult, _Mapping]]] = ..., status: _Optional[int] = ..., sweepType: _Optional[int] = ..., totalGp: _Optional[int] = ..., dropItems: _Optional[_Iterable[_Union[ItemTemplate, _Mapping]]] = ..., campaignId: _Optional[int] = ...) -> None: ...

class CampaignTakeCardsMsg(_message.Message):
    __slots__ = ("playerId", "name", "pay", "index", "templateId", "count", "bind", "randomSkill_1", "randomSkill_2", "randomSkill_3", "randomSkill_4", "randomSkill_5")
    PLAYERID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    PAY_FIELD_NUMBER: _ClassVar[int]
    INDEX_FIELD_NUMBER: _ClassVar[int]
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    BIND_FIELD_NUMBER: _ClassVar[int]
    RANDOMSKILL_1_FIELD_NUMBER: _ClassVar[int]
    RANDOMSKILL_2_FIELD_NUMBER: _ClassVar[int]
    RANDOMSKILL_3_FIELD_NUMBER: _ClassVar[int]
    RANDOMSKILL_4_FIELD_NUMBER: _ClassVar[int]
    RANDOMSKILL_5_FIELD_NUMBER: _ClassVar[int]
    playerId: int
    name: str
    pay: bool
    index: int
    templateId: int
    count: int
    bind: bool
    randomSkill_1: int
    randomSkill_2: int
    randomSkill_3: int
    randomSkill_4: int
    randomSkill_5: int
    def __init__(self, playerId: _Optional[int] = ..., name: _Optional[str] = ..., pay: _Optional[bool] = ..., index: _Optional[int] = ..., templateId: _Optional[int] = ..., count: _Optional[int] = ..., bind: _Optional[bool] = ..., randomSkill_1: _Optional[int] = ..., randomSkill_2: _Optional[int] = ..., randomSkill_3: _Optional[int] = ..., randomSkill_4: _Optional[int] = ..., randomSkill_5: _Optional[int] = ...) -> None: ...

class CanceltemRspMsg(_message.Message):
    __slots__ = ("result", "id", "item")
    RESULT_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    ITEM_FIELD_NUMBER: _ClassVar[int]
    result: int
    id: int
    item: MallItemMsg
    def __init__(self, result: _Optional[int] = ..., id: _Optional[int] = ..., item: _Optional[_Union[MallItemMsg, _Mapping]] = ...) -> None: ...

class CaptainSpeakMsg(_message.Message):
    __slots__ = ("cmapaignName", "roomId", "isLock", "inviteContent", "type")
    CMAPAIGNNAME_FIELD_NUMBER: _ClassVar[int]
    ROOMID_FIELD_NUMBER: _ClassVar[int]
    ISLOCK_FIELD_NUMBER: _ClassVar[int]
    INVITECONTENT_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    cmapaignName: str
    roomId: int
    isLock: int
    inviteContent: _containers.RepeatedScalarFieldContainer[str]
    type: int
    def __init__(self, cmapaignName: _Optional[str] = ..., roomId: _Optional[int] = ..., isLock: _Optional[int] = ..., inviteContent: _Optional[_Iterable[str]] = ..., type: _Optional[int] = ...) -> None: ...

class CarInfo(_message.Message):
    __slots__ = ("userId", "minerals", "quality", "tramcarCount", "handCount", "isOwn", "pickCount", "armyId")
    USERID_FIELD_NUMBER: _ClassVar[int]
    MINERALS_FIELD_NUMBER: _ClassVar[int]
    QUALITY_FIELD_NUMBER: _ClassVar[int]
    TRAMCARCOUNT_FIELD_NUMBER: _ClassVar[int]
    HANDCOUNT_FIELD_NUMBER: _ClassVar[int]
    ISOWN_FIELD_NUMBER: _ClassVar[int]
    PICKCOUNT_FIELD_NUMBER: _ClassVar[int]
    ARMYID_FIELD_NUMBER: _ClassVar[int]
    userId: int
    minerals: int
    quality: int
    tramcarCount: int
    handCount: int
    isOwn: int
    pickCount: int
    armyId: int
    def __init__(self, userId: _Optional[int] = ..., minerals: _Optional[int] = ..., quality: _Optional[int] = ..., tramcarCount: _Optional[int] = ..., handCount: _Optional[int] = ..., isOwn: _Optional[int] = ..., pickCount: _Optional[int] = ..., armyId: _Optional[int] = ...) -> None: ...

class CastDiceMsg(_message.Message):
    __slots__ = ("curPos", "diceNumber", "score", "tempIds")
    CURPOS_FIELD_NUMBER: _ClassVar[int]
    DICENUMBER_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    TEMPIDS_FIELD_NUMBER: _ClassVar[int]
    curPos: int
    diceNumber: int
    score: int
    tempIds: str
    def __init__(self, curPos: _Optional[int] = ..., diceNumber: _Optional[int] = ..., score: _Optional[int] = ..., tempIds: _Optional[str] = ...) -> None: ...

class CastleDefenseRspMsg(_message.Message):
    __slots__ = ("posX", "posY", "leftTime")
    POSX_FIELD_NUMBER: _ClassVar[int]
    POSY_FIELD_NUMBER: _ClassVar[int]
    LEFTTIME_FIELD_NUMBER: _ClassVar[int]
    posX: int
    posY: int
    leftTime: int
    def __init__(self, posX: _Optional[int] = ..., posY: _Optional[int] = ..., leftTime: _Optional[int] = ...) -> None: ...

class CastleReqMsg(_message.Message):
    __slots__ = ("magId", "posX", "posY", "leftTime", "leftEnergy", "payType")
    MAGID_FIELD_NUMBER: _ClassVar[int]
    POSX_FIELD_NUMBER: _ClassVar[int]
    POSY_FIELD_NUMBER: _ClassVar[int]
    LEFTTIME_FIELD_NUMBER: _ClassVar[int]
    LEFTENERGY_FIELD_NUMBER: _ClassVar[int]
    PAYTYPE_FIELD_NUMBER: _ClassVar[int]
    magId: int
    posX: int
    posY: int
    leftTime: int
    leftEnergy: int
    payType: int
    def __init__(self, magId: _Optional[int] = ..., posX: _Optional[int] = ..., posY: _Optional[int] = ..., leftTime: _Optional[int] = ..., leftEnergy: _Optional[int] = ..., payType: _Optional[int] = ...) -> None: ...

class CastleYieldMsg(_message.Message):
    __slots__ = ("goldYield", "goldWildLandYield", "goldTechnology", "goldWonder", "goldDower", "goldTotalCount", "goldMax", "curPopulation", "maxPopulation", "wildYield", "crystalsCount")
    GOLDYIELD_FIELD_NUMBER: _ClassVar[int]
    GOLDWILDLANDYIELD_FIELD_NUMBER: _ClassVar[int]
    GOLDTECHNOLOGY_FIELD_NUMBER: _ClassVar[int]
    GOLDWONDER_FIELD_NUMBER: _ClassVar[int]
    GOLDDOWER_FIELD_NUMBER: _ClassVar[int]
    GOLDTOTALCOUNT_FIELD_NUMBER: _ClassVar[int]
    GOLDMAX_FIELD_NUMBER: _ClassVar[int]
    CURPOPULATION_FIELD_NUMBER: _ClassVar[int]
    MAXPOPULATION_FIELD_NUMBER: _ClassVar[int]
    WILDYIELD_FIELD_NUMBER: _ClassVar[int]
    CRYSTALSCOUNT_FIELD_NUMBER: _ClassVar[int]
    goldYield: int
    goldWildLandYield: int
    goldTechnology: int
    goldWonder: int
    goldDower: int
    goldTotalCount: int
    goldMax: int
    curPopulation: int
    maxPopulation: int
    wildYield: _containers.RepeatedCompositeFieldContainer[WildYieldMsg]
    crystalsCount: int
    def __init__(self, goldYield: _Optional[int] = ..., goldWildLandYield: _Optional[int] = ..., goldTechnology: _Optional[int] = ..., goldWonder: _Optional[int] = ..., goldDower: _Optional[int] = ..., goldTotalCount: _Optional[int] = ..., goldMax: _Optional[int] = ..., curPopulation: _Optional[int] = ..., maxPopulation: _Optional[int] = ..., wildYield: _Optional[_Iterable[_Union[WildYieldMsg, _Mapping]]] = ..., crystalsCount: _Optional[int] = ...) -> None: ...

class CellInfoMsg(_message.Message):
    __slots__ = ("itemID", "count")
    ITEMID_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    itemID: int
    count: int
    def __init__(self, itemID: _Optional[int] = ..., count: _Optional[int] = ...) -> None: ...

class ChairsChargeMsg(_message.Message):
    __slots__ = ("userId", "totalPoint", "currentPoint", "tokenCount", "uuid", "site", "serverName", "param1", "param2")
    USERID_FIELD_NUMBER: _ClassVar[int]
    TOTALPOINT_FIELD_NUMBER: _ClassVar[int]
    CURRENTPOINT_FIELD_NUMBER: _ClassVar[int]
    TOKENCOUNT_FIELD_NUMBER: _ClassVar[int]
    UUID_FIELD_NUMBER: _ClassVar[int]
    SITE_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    PARAM1_FIELD_NUMBER: _ClassVar[int]
    PARAM2_FIELD_NUMBER: _ClassVar[int]
    userId: int
    totalPoint: int
    currentPoint: int
    tokenCount: int
    uuid: str
    site: str
    serverName: str
    param1: int
    param2: int
    def __init__(self, userId: _Optional[int] = ..., totalPoint: _Optional[int] = ..., currentPoint: _Optional[int] = ..., tokenCount: _Optional[int] = ..., uuid: _Optional[str] = ..., site: _Optional[str] = ..., serverName: _Optional[str] = ..., param1: _Optional[int] = ..., param2: _Optional[int] = ...) -> None: ...

class ChairsListMsg(_message.Message):
    __slots__ = ("op", "totalChairsCount", "reward", "charge", "userId", "luckyNickName", "currentChairs", "rewardCounts", "rewardNeedChairs", "chairsNeedPoints", "openTime", "stopTime", "chairsNum", "luckyItems", "comfortItems", "leftPoint")
    OP_FIELD_NUMBER: _ClassVar[int]
    TOTALCHAIRSCOUNT_FIELD_NUMBER: _ClassVar[int]
    REWARD_FIELD_NUMBER: _ClassVar[int]
    CHARGE_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    LUCKYNICKNAME_FIELD_NUMBER: _ClassVar[int]
    CURRENTCHAIRS_FIELD_NUMBER: _ClassVar[int]
    REWARDCOUNTS_FIELD_NUMBER: _ClassVar[int]
    REWARDNEEDCHAIRS_FIELD_NUMBER: _ClassVar[int]
    CHAIRSNEEDPOINTS_FIELD_NUMBER: _ClassVar[int]
    OPENTIME_FIELD_NUMBER: _ClassVar[int]
    STOPTIME_FIELD_NUMBER: _ClassVar[int]
    CHAIRSNUM_FIELD_NUMBER: _ClassVar[int]
    LUCKYITEMS_FIELD_NUMBER: _ClassVar[int]
    COMFORTITEMS_FIELD_NUMBER: _ClassVar[int]
    LEFTPOINT_FIELD_NUMBER: _ClassVar[int]
    op: int
    totalChairsCount: int
    reward: _containers.RepeatedCompositeFieldContainer[ChairsRewardMsg]
    charge: _containers.RepeatedCompositeFieldContainer[ChairsChargeMsg]
    userId: int
    luckyNickName: _containers.RepeatedScalarFieldContainer[str]
    currentChairs: int
    rewardCounts: int
    rewardNeedChairs: int
    chairsNeedPoints: int
    openTime: str
    stopTime: str
    chairsNum: str
    luckyItems: _containers.RepeatedScalarFieldContainer[str]
    comfortItems: _containers.RepeatedScalarFieldContainer[str]
    leftPoint: int
    def __init__(self, op: _Optional[int] = ..., totalChairsCount: _Optional[int] = ..., reward: _Optional[_Iterable[_Union[ChairsRewardMsg, _Mapping]]] = ..., charge: _Optional[_Iterable[_Union[ChairsChargeMsg, _Mapping]]] = ..., userId: _Optional[int] = ..., luckyNickName: _Optional[_Iterable[str]] = ..., currentChairs: _Optional[int] = ..., rewardCounts: _Optional[int] = ..., rewardNeedChairs: _Optional[int] = ..., chairsNeedPoints: _Optional[int] = ..., openTime: _Optional[str] = ..., stopTime: _Optional[str] = ..., chairsNum: _Optional[str] = ..., luckyItems: _Optional[_Iterable[str]] = ..., comfortItems: _Optional[_Iterable[str]] = ..., leftPoint: _Optional[int] = ...) -> None: ...

class ChairsRewardMsg(_message.Message):
    __slots__ = ("cCCActiveUUID", "uUID", "userId", "tokenChairs", "rewardTypes", "rewardState", "serverName")
    CCCACTIVEUUID_FIELD_NUMBER: _ClassVar[int]
    UUID_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    TOKENCHAIRS_FIELD_NUMBER: _ClassVar[int]
    REWARDTYPES_FIELD_NUMBER: _ClassVar[int]
    REWARDSTATE_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    cCCActiveUUID: str
    uUID: str
    userId: int
    tokenChairs: str
    rewardTypes: int
    rewardState: int
    serverName: str
    def __init__(self, cCCActiveUUID: _Optional[str] = ..., uUID: _Optional[str] = ..., userId: _Optional[int] = ..., tokenChairs: _Optional[str] = ..., rewardTypes: _Optional[int] = ..., rewardState: _Optional[int] = ..., serverName: _Optional[str] = ...) -> None: ...

class ChallengeCoolTimeMsg(_message.Message):
    __slots__ = ("leftTime", "challengeCount", "totalCount", "type", "totalBuyCount")
    LEFTTIME_FIELD_NUMBER: _ClassVar[int]
    CHALLENGECOUNT_FIELD_NUMBER: _ClassVar[int]
    TOTALCOUNT_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    TOTALBUYCOUNT_FIELD_NUMBER: _ClassVar[int]
    leftTime: int
    challengeCount: int
    totalCount: int
    type: int
    totalBuyCount: int
    def __init__(self, leftTime: _Optional[int] = ..., challengeCount: _Optional[int] = ..., totalCount: _Optional[int] = ..., type: _Optional[int] = ..., totalBuyCount: _Optional[int] = ...) -> None: ...

class ChallengeGuildMsg(_message.Message):
    __slots__ = ("giveOffer", "tarGuildId")
    GIVEOFFER_FIELD_NUMBER: _ClassVar[int]
    TARGUILDID_FIELD_NUMBER: _ClassVar[int]
    giveOffer: int
    tarGuildId: int
    def __init__(self, giveOffer: _Optional[int] = ..., tarGuildId: _Optional[int] = ...) -> None: ...

class ChallengeInfoMsg(_message.Message):
    __slots__ = ("lastWinCount", "challengeCount", "curRank", "simplePlayer", "challengeLog", "noticMsg", "avater", "leftDay", "totalCount", "totalBuyCount")
    LASTWINCOUNT_FIELD_NUMBER: _ClassVar[int]
    CHALLENGECOUNT_FIELD_NUMBER: _ClassVar[int]
    CURRANK_FIELD_NUMBER: _ClassVar[int]
    SIMPLEPLAYER_FIELD_NUMBER: _ClassVar[int]
    CHALLENGELOG_FIELD_NUMBER: _ClassVar[int]
    NOTICMSG_FIELD_NUMBER: _ClassVar[int]
    AVATER_FIELD_NUMBER: _ClassVar[int]
    LEFTDAY_FIELD_NUMBER: _ClassVar[int]
    TOTALCOUNT_FIELD_NUMBER: _ClassVar[int]
    TOTALBUYCOUNT_FIELD_NUMBER: _ClassVar[int]
    lastWinCount: int
    challengeCount: int
    curRank: int
    simplePlayer: _containers.RepeatedCompositeFieldContainer[SimplePlayerInfoMsg]
    challengeLog: _containers.RepeatedCompositeFieldContainer[ChallengeLogMsg]
    noticMsg: str
    avater: _containers.RepeatedCompositeFieldContainer[AvaterMsg]
    leftDay: int
    totalCount: int
    totalBuyCount: int
    def __init__(self, lastWinCount: _Optional[int] = ..., challengeCount: _Optional[int] = ..., curRank: _Optional[int] = ..., simplePlayer: _Optional[_Iterable[_Union[SimplePlayerInfoMsg, _Mapping]]] = ..., challengeLog: _Optional[_Iterable[_Union[ChallengeLogMsg, _Mapping]]] = ..., noticMsg: _Optional[str] = ..., avater: _Optional[_Iterable[_Union[AvaterMsg, _Mapping]]] = ..., leftDay: _Optional[int] = ..., totalCount: _Optional[int] = ..., totalBuyCount: _Optional[int] = ...) -> None: ...

class ChallengeLogMsg(_message.Message):
    __slots__ = ("userId", "result", "tarUserId", "tarNickName", "isAttack", "logDate", "curRankResult", "grades", "gpOrder", "gp", "job", "forward")
    USERID_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    TARUSERID_FIELD_NUMBER: _ClassVar[int]
    TARNICKNAME_FIELD_NUMBER: _ClassVar[int]
    ISATTACK_FIELD_NUMBER: _ClassVar[int]
    LOGDATE_FIELD_NUMBER: _ClassVar[int]
    CURRANKRESULT_FIELD_NUMBER: _ClassVar[int]
    GRADES_FIELD_NUMBER: _ClassVar[int]
    GPORDER_FIELD_NUMBER: _ClassVar[int]
    GP_FIELD_NUMBER: _ClassVar[int]
    JOB_FIELD_NUMBER: _ClassVar[int]
    FORWARD_FIELD_NUMBER: _ClassVar[int]
    userId: int
    result: int
    tarUserId: int
    tarNickName: str
    isAttack: bool
    logDate: str
    curRankResult: int
    grades: int
    gpOrder: int
    gp: int
    job: int
    forward: int
    def __init__(self, userId: _Optional[int] = ..., result: _Optional[int] = ..., tarUserId: _Optional[int] = ..., tarNickName: _Optional[str] = ..., isAttack: _Optional[bool] = ..., logDate: _Optional[str] = ..., curRankResult: _Optional[int] = ..., grades: _Optional[int] = ..., gpOrder: _Optional[int] = ..., gp: _Optional[int] = ..., job: _Optional[int] = ..., forward: _Optional[int] = ...) -> None: ...

class ChallengeRankRewardMsg(_message.Message):
    __slots__ = ("isTake", "param1", "param2", "param3", "param4")
    ISTAKE_FIELD_NUMBER: _ClassVar[int]
    PARAM1_FIELD_NUMBER: _ClassVar[int]
    PARAM2_FIELD_NUMBER: _ClassVar[int]
    PARAM3_FIELD_NUMBER: _ClassVar[int]
    PARAM4_FIELD_NUMBER: _ClassVar[int]
    isTake: bool
    param1: int
    param2: int
    param3: int
    param4: int
    def __init__(self, isTake: _Optional[bool] = ..., param1: _Optional[int] = ..., param2: _Optional[int] = ..., param3: _Optional[int] = ..., param4: _Optional[int] = ...) -> None: ...

class ChallengeRequestMsg(_message.Message):
    __slots__ = ("type",)
    TYPE_FIELD_NUMBER: _ClassVar[int]
    type: int
    def __init__(self, type: _Optional[int] = ...) -> None: ...

class ChallengeRewardMsg(_message.Message):
    __slots__ = ("userId", "message", "items")
    USERID_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    ITEMS_FIELD_NUMBER: _ClassVar[int]
    userId: int
    message: str
    items: str
    def __init__(self, userId: _Optional[int] = ..., message: _Optional[str] = ..., items: _Optional[str] = ...) -> None: ...

class ChallengeScoreMsg(_message.Message):
    __slots__ = ("userId", "tollgateId", "score", "order", "isLucky", "nickName", "isVip", "grade", "consortiaName", "fightCapacity")
    USERID_FIELD_NUMBER: _ClassVar[int]
    TOLLGATEID_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    ORDER_FIELD_NUMBER: _ClassVar[int]
    ISLUCKY_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    ISVIP_FIELD_NUMBER: _ClassVar[int]
    GRADE_FIELD_NUMBER: _ClassVar[int]
    CONSORTIANAME_FIELD_NUMBER: _ClassVar[int]
    FIGHTCAPACITY_FIELD_NUMBER: _ClassVar[int]
    userId: int
    tollgateId: int
    score: int
    order: int
    isLucky: bool
    nickName: str
    isVip: bool
    grade: int
    consortiaName: str
    fightCapacity: int
    def __init__(self, userId: _Optional[int] = ..., tollgateId: _Optional[int] = ..., score: _Optional[int] = ..., order: _Optional[int] = ..., isLucky: _Optional[bool] = ..., nickName: _Optional[str] = ..., isVip: _Optional[bool] = ..., grade: _Optional[int] = ..., consortiaName: _Optional[str] = ..., fightCapacity: _Optional[int] = ...) -> None: ...

class ChangeMasterRspMsg(_message.Message):
    __slots__ = ("roomId", "masterId")
    ROOMID_FIELD_NUMBER: _ClassVar[int]
    MASTERID_FIELD_NUMBER: _ClassVar[int]
    roomId: int
    masterId: int
    def __init__(self, roomId: _Optional[int] = ..., masterId: _Optional[int] = ...) -> None: ...

class ChargeRewardMsg(_message.Message):
    __slots__ = ("totalCount", "topThreeCount", "myTotalCount", "dayTotalCount")
    TOTALCOUNT_FIELD_NUMBER: _ClassVar[int]
    TOPTHREECOUNT_FIELD_NUMBER: _ClassVar[int]
    MYTOTALCOUNT_FIELD_NUMBER: _ClassVar[int]
    DAYTOTALCOUNT_FIELD_NUMBER: _ClassVar[int]
    totalCount: int
    topThreeCount: int
    myTotalCount: int
    dayTotalCount: int
    def __init__(self, totalCount: _Optional[int] = ..., topThreeCount: _Optional[int] = ..., myTotalCount: _Optional[int] = ..., dayTotalCount: _Optional[int] = ...) -> None: ...

class ChatChannelMsg(_message.Message):
    __slots__ = ("channel", "type", "encodeMsg", "otherId", "name", "team", "consortiaId", "consortiaName", "userType", "limitGrade", "maxGrade", "isCenterTip", "isBigTip", "vipGrade", "expUserIds", "bigBugleType", "items", "stars", "powcards", "serverName", "battleId", "isImportant", "appellid", "job", "receiveName", "vipType")
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    ENCODEMSG_FIELD_NUMBER: _ClassVar[int]
    OTHERID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TEAM_FIELD_NUMBER: _ClassVar[int]
    CONSORTIAID_FIELD_NUMBER: _ClassVar[int]
    CONSORTIANAME_FIELD_NUMBER: _ClassVar[int]
    USERTYPE_FIELD_NUMBER: _ClassVar[int]
    LIMITGRADE_FIELD_NUMBER: _ClassVar[int]
    MAXGRADE_FIELD_NUMBER: _ClassVar[int]
    ISCENTERTIP_FIELD_NUMBER: _ClassVar[int]
    ISBIGTIP_FIELD_NUMBER: _ClassVar[int]
    VIPGRADE_FIELD_NUMBER: _ClassVar[int]
    EXPUSERIDS_FIELD_NUMBER: _ClassVar[int]
    BIGBUGLETYPE_FIELD_NUMBER: _ClassVar[int]
    ITEMS_FIELD_NUMBER: _ClassVar[int]
    STARS_FIELD_NUMBER: _ClassVar[int]
    POWCARDS_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    BATTLEID_FIELD_NUMBER: _ClassVar[int]
    ISIMPORTANT_FIELD_NUMBER: _ClassVar[int]
    APPELLID_FIELD_NUMBER: _ClassVar[int]
    JOB_FIELD_NUMBER: _ClassVar[int]
    RECEIVENAME_FIELD_NUMBER: _ClassVar[int]
    VIPTYPE_FIELD_NUMBER: _ClassVar[int]
    channel: int
    type: int
    encodeMsg: str
    otherId: int
    name: str
    team: _containers.RepeatedScalarFieldContainer[int]
    consortiaId: int
    consortiaName: str
    userType: int
    limitGrade: int
    maxGrade: int
    isCenterTip: bool
    isBigTip: bool
    vipGrade: int
    expUserIds: _containers.RepeatedScalarFieldContainer[int]
    bigBugleType: int
    items: _containers.RepeatedCompositeFieldContainer[ChatItemInfoMsg]
    stars: _containers.RepeatedCompositeFieldContainer[ChatStarInfoMsg]
    powcards: _containers.RepeatedCompositeFieldContainer[ChatPowCardInfoMsg]
    serverName: str
    battleId: str
    isImportant: bool
    appellid: int
    job: int
    receiveName: str
    vipType: int
    def __init__(self, channel: _Optional[int] = ..., type: _Optional[int] = ..., encodeMsg: _Optional[str] = ..., otherId: _Optional[int] = ..., name: _Optional[str] = ..., team: _Optional[_Iterable[int]] = ..., consortiaId: _Optional[int] = ..., consortiaName: _Optional[str] = ..., userType: _Optional[int] = ..., limitGrade: _Optional[int] = ..., maxGrade: _Optional[int] = ..., isCenterTip: _Optional[bool] = ..., isBigTip: _Optional[bool] = ..., vipGrade: _Optional[int] = ..., expUserIds: _Optional[_Iterable[int]] = ..., bigBugleType: _Optional[int] = ..., items: _Optional[_Iterable[_Union[ChatItemInfoMsg, _Mapping]]] = ..., stars: _Optional[_Iterable[_Union[ChatStarInfoMsg, _Mapping]]] = ..., powcards: _Optional[_Iterable[_Union[ChatPowCardInfoMsg, _Mapping]]] = ..., serverName: _Optional[str] = ..., battleId: _Optional[str] = ..., isImportant: _Optional[bool] = ..., appellid: _Optional[int] = ..., job: _Optional[int] = ..., receiveName: _Optional[str] = ..., vipType: _Optional[int] = ...) -> None: ...

class ChatFriendMsg(_message.Message):
    __slots__ = ("fromId", "fromNick", "toId", "encodeMsg", "sendDate", "result")
    FROMID_FIELD_NUMBER: _ClassVar[int]
    FROMNICK_FIELD_NUMBER: _ClassVar[int]
    TOID_FIELD_NUMBER: _ClassVar[int]
    ENCODEMSG_FIELD_NUMBER: _ClassVar[int]
    SENDDATE_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    fromId: int
    fromNick: str
    toId: int
    encodeMsg: str
    sendDate: str
    result: int
    def __init__(self, fromId: _Optional[int] = ..., fromNick: _Optional[str] = ..., toId: _Optional[int] = ..., encodeMsg: _Optional[str] = ..., sendDate: _Optional[str] = ..., result: _Optional[int] = ...) -> None: ...

class ChatItemInfoMsg(_message.Message):
    __slots__ = ("id", "templateId", "pos", "exist", "objectId", "bagType", "bind", "used", "validDate", "beginDate", "count", "attack", "defence", "agility", "ability", "captain", "strengthenGrade", "join_1", "join_2", "join_3", "randomSkill_1", "randomSkill_2", "randomSkill_3", "randomSkill_4", "randomSkill_5", "isNew", "userId", "itemName", "join_4", "property1", "mouldGrade", "appraisalSkill")
    ID_FIELD_NUMBER: _ClassVar[int]
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    POS_FIELD_NUMBER: _ClassVar[int]
    EXIST_FIELD_NUMBER: _ClassVar[int]
    OBJECTID_FIELD_NUMBER: _ClassVar[int]
    BAGTYPE_FIELD_NUMBER: _ClassVar[int]
    BIND_FIELD_NUMBER: _ClassVar[int]
    USED_FIELD_NUMBER: _ClassVar[int]
    VALIDDATE_FIELD_NUMBER: _ClassVar[int]
    BEGINDATE_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    ATTACK_FIELD_NUMBER: _ClassVar[int]
    DEFENCE_FIELD_NUMBER: _ClassVar[int]
    AGILITY_FIELD_NUMBER: _ClassVar[int]
    ABILITY_FIELD_NUMBER: _ClassVar[int]
    CAPTAIN_FIELD_NUMBER: _ClassVar[int]
    STRENGTHENGRADE_FIELD_NUMBER: _ClassVar[int]
    JOIN_1_FIELD_NUMBER: _ClassVar[int]
    JOIN_2_FIELD_NUMBER: _ClassVar[int]
    JOIN_3_FIELD_NUMBER: _ClassVar[int]
    RANDOMSKILL_1_FIELD_NUMBER: _ClassVar[int]
    RANDOMSKILL_2_FIELD_NUMBER: _ClassVar[int]
    RANDOMSKILL_3_FIELD_NUMBER: _ClassVar[int]
    RANDOMSKILL_4_FIELD_NUMBER: _ClassVar[int]
    RANDOMSKILL_5_FIELD_NUMBER: _ClassVar[int]
    ISNEW_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    ITEMNAME_FIELD_NUMBER: _ClassVar[int]
    JOIN_4_FIELD_NUMBER: _ClassVar[int]
    PROPERTY1_FIELD_NUMBER: _ClassVar[int]
    MOULDGRADE_FIELD_NUMBER: _ClassVar[int]
    APPRAISALSKILL_FIELD_NUMBER: _ClassVar[int]
    id: int
    templateId: int
    pos: int
    exist: bool
    objectId: int
    bagType: int
    bind: bool
    used: bool
    validDate: int
    beginDate: bytes
    count: int
    attack: int
    defence: int
    agility: int
    ability: int
    captain: int
    strengthenGrade: int
    join_1: int
    join_2: int
    join_3: int
    randomSkill_1: int
    randomSkill_2: int
    randomSkill_3: int
    randomSkill_4: int
    randomSkill_5: int
    isNew: bool
    userId: int
    itemName: str
    join_4: int
    property1: str
    mouldGrade: int
    appraisalSkill: int
    def __init__(self, id: _Optional[int] = ..., templateId: _Optional[int] = ..., pos: _Optional[int] = ..., exist: _Optional[bool] = ..., objectId: _Optional[int] = ..., bagType: _Optional[int] = ..., bind: _Optional[bool] = ..., used: _Optional[bool] = ..., validDate: _Optional[int] = ..., beginDate: _Optional[bytes] = ..., count: _Optional[int] = ..., attack: _Optional[int] = ..., defence: _Optional[int] = ..., agility: _Optional[int] = ..., ability: _Optional[int] = ..., captain: _Optional[int] = ..., strengthenGrade: _Optional[int] = ..., join_1: _Optional[int] = ..., join_2: _Optional[int] = ..., join_3: _Optional[int] = ..., randomSkill_1: _Optional[int] = ..., randomSkill_2: _Optional[int] = ..., randomSkill_3: _Optional[int] = ..., randomSkill_4: _Optional[int] = ..., randomSkill_5: _Optional[int] = ..., isNew: _Optional[bool] = ..., userId: _Optional[int] = ..., itemName: _Optional[str] = ..., join_4: _Optional[int] = ..., property1: _Optional[str] = ..., mouldGrade: _Optional[int] = ..., appraisalSkill: _Optional[int] = ...) -> None: ...

class ChatPowCardInfoMsg(_message.Message):
    __slots__ = ("id", "templateId", "userId", "objectId", "pos", "exist", "bagType", "grade", "gp", "isLock", "powcardName", "buffId", "sonType", "fixValue", "percent")
    ID_FIELD_NUMBER: _ClassVar[int]
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    OBJECTID_FIELD_NUMBER: _ClassVar[int]
    POS_FIELD_NUMBER: _ClassVar[int]
    EXIST_FIELD_NUMBER: _ClassVar[int]
    BAGTYPE_FIELD_NUMBER: _ClassVar[int]
    GRADE_FIELD_NUMBER: _ClassVar[int]
    GP_FIELD_NUMBER: _ClassVar[int]
    ISLOCK_FIELD_NUMBER: _ClassVar[int]
    POWCARDNAME_FIELD_NUMBER: _ClassVar[int]
    BUFFID_FIELD_NUMBER: _ClassVar[int]
    SONTYPE_FIELD_NUMBER: _ClassVar[int]
    FIXVALUE_FIELD_NUMBER: _ClassVar[int]
    PERCENT_FIELD_NUMBER: _ClassVar[int]
    id: int
    templateId: int
    userId: int
    objectId: int
    pos: int
    exist: bool
    bagType: int
    grade: int
    gp: int
    isLock: bool
    powcardName: str
    buffId: int
    sonType: int
    fixValue: int
    percent: int
    def __init__(self, id: _Optional[int] = ..., templateId: _Optional[int] = ..., userId: _Optional[int] = ..., objectId: _Optional[int] = ..., pos: _Optional[int] = ..., exist: _Optional[bool] = ..., bagType: _Optional[int] = ..., grade: _Optional[int] = ..., gp: _Optional[int] = ..., isLock: _Optional[bool] = ..., powcardName: _Optional[str] = ..., buffId: _Optional[int] = ..., sonType: _Optional[int] = ..., fixValue: _Optional[int] = ..., percent: _Optional[int] = ...) -> None: ...

class ChatStarInfoMsg(_message.Message):
    __slots__ = ("id", "templateId", "userId", "objectId", "pos", "exist", "bagType", "grade", "gp", "isLock", "starName")
    ID_FIELD_NUMBER: _ClassVar[int]
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    OBJECTID_FIELD_NUMBER: _ClassVar[int]
    POS_FIELD_NUMBER: _ClassVar[int]
    EXIST_FIELD_NUMBER: _ClassVar[int]
    BAGTYPE_FIELD_NUMBER: _ClassVar[int]
    GRADE_FIELD_NUMBER: _ClassVar[int]
    GP_FIELD_NUMBER: _ClassVar[int]
    ISLOCK_FIELD_NUMBER: _ClassVar[int]
    STARNAME_FIELD_NUMBER: _ClassVar[int]
    id: int
    templateId: int
    userId: int
    objectId: int
    pos: int
    exist: bool
    bagType: int
    grade: int
    gp: int
    isLock: bool
    starName: str
    def __init__(self, id: _Optional[int] = ..., templateId: _Optional[int] = ..., userId: _Optional[int] = ..., objectId: _Optional[int] = ..., pos: _Optional[int] = ..., exist: _Optional[bool] = ..., bagType: _Optional[int] = ..., grade: _Optional[int] = ..., gp: _Optional[int] = ..., isLock: _Optional[bool] = ..., starName: _Optional[str] = ...) -> None: ...

class ChatStateListRspMsg(_message.Message):
    __slots__ = ("chatState",)
    CHATSTATE_FIELD_NUMBER: _ClassVar[int]
    chatState: _containers.RepeatedCompositeFieldContainer[ChatStateMsg]
    def __init__(self, chatState: _Optional[_Iterable[_Union[ChatStateMsg, _Mapping]]] = ...) -> None: ...

class ChatStateMsg(_message.Message):
    __slots__ = ("userId", "chatState", "result", "replayStr")
    USERID_FIELD_NUMBER: _ClassVar[int]
    CHATSTATE_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    REPLAYSTR_FIELD_NUMBER: _ClassVar[int]
    userId: int
    chatState: int
    result: int
    replayStr: str
    def __init__(self, userId: _Optional[int] = ..., chatState: _Optional[int] = ..., result: _Optional[int] = ..., replayStr: _Optional[str] = ...) -> None: ...

class CheckImageMsg(_message.Message):
    __slots__ = ("leftCount", "leftTime", "images1", "images2", "images3", "images4", "result", "property1", "property2")
    LEFTCOUNT_FIELD_NUMBER: _ClassVar[int]
    LEFTTIME_FIELD_NUMBER: _ClassVar[int]
    IMAGES1_FIELD_NUMBER: _ClassVar[int]
    IMAGES2_FIELD_NUMBER: _ClassVar[int]
    IMAGES3_FIELD_NUMBER: _ClassVar[int]
    IMAGES4_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    PROPERTY1_FIELD_NUMBER: _ClassVar[int]
    PROPERTY2_FIELD_NUMBER: _ClassVar[int]
    leftCount: int
    leftTime: int
    images1: bytes
    images2: bytes
    images3: bytes
    images4: bytes
    result: str
    property1: str
    property2: str
    def __init__(self, leftCount: _Optional[int] = ..., leftTime: _Optional[int] = ..., images1: _Optional[bytes] = ..., images2: _Optional[bytes] = ..., images3: _Optional[bytes] = ..., images4: _Optional[bytes] = ..., result: _Optional[str] = ..., property1: _Optional[str] = ..., property2: _Optional[str] = ...) -> None: ...

class CheckNickMsg(_message.Message):
    __slots__ = ("playerId", "nickName")
    PLAYERID_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    playerId: int
    nickName: str
    def __init__(self, playerId: _Optional[int] = ..., nickName: _Optional[str] = ...) -> None: ...

class CheckSend(_message.Message):
    __slots__ = ("canSend",)
    CANSEND_FIELD_NUMBER: _ClassVar[int]
    canSend: int
    def __init__(self, canSend: _Optional[int] = ...) -> None: ...

class ChildEquipmentMsg(_message.Message):
    __slots__ = ("templateId", "pos", "join1", "join2", "join3", "join4", "randomSkill1", "randomSkill2", "randomSkill3", "randomSkill4", "randomSkill5", "mouldGrade", "isBind", "strengthenGrade")
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    POS_FIELD_NUMBER: _ClassVar[int]
    JOIN1_FIELD_NUMBER: _ClassVar[int]
    JOIN2_FIELD_NUMBER: _ClassVar[int]
    JOIN3_FIELD_NUMBER: _ClassVar[int]
    JOIN4_FIELD_NUMBER: _ClassVar[int]
    RANDOMSKILL1_FIELD_NUMBER: _ClassVar[int]
    RANDOMSKILL2_FIELD_NUMBER: _ClassVar[int]
    RANDOMSKILL3_FIELD_NUMBER: _ClassVar[int]
    RANDOMSKILL4_FIELD_NUMBER: _ClassVar[int]
    RANDOMSKILL5_FIELD_NUMBER: _ClassVar[int]
    MOULDGRADE_FIELD_NUMBER: _ClassVar[int]
    ISBIND_FIELD_NUMBER: _ClassVar[int]
    STRENGTHENGRADE_FIELD_NUMBER: _ClassVar[int]
    templateId: int
    pos: int
    join1: int
    join2: int
    join3: int
    join4: int
    randomSkill1: int
    randomSkill2: int
    randomSkill3: int
    randomSkill4: int
    randomSkill5: int
    mouldGrade: int
    isBind: bool
    strengthenGrade: int
    def __init__(self, templateId: _Optional[int] = ..., pos: _Optional[int] = ..., join1: _Optional[int] = ..., join2: _Optional[int] = ..., join3: _Optional[int] = ..., join4: _Optional[int] = ..., randomSkill1: _Optional[int] = ..., randomSkill2: _Optional[int] = ..., randomSkill3: _Optional[int] = ..., randomSkill4: _Optional[int] = ..., randomSkill5: _Optional[int] = ..., mouldGrade: _Optional[int] = ..., isBind: _Optional[bool] = ..., strengthenGrade: _Optional[int] = ...) -> None: ...

class ChildrenInfoMsg(_message.Message):
    __slots__ = ("childId", "name", "job", "sex", "userIdA", "userIdB", "growthGrade", "mood", "growthGp", "growthCount", "fightCapacity", "state", "equipmets", "emblem")
    CHILDID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    JOB_FIELD_NUMBER: _ClassVar[int]
    SEX_FIELD_NUMBER: _ClassVar[int]
    USERIDA_FIELD_NUMBER: _ClassVar[int]
    USERIDB_FIELD_NUMBER: _ClassVar[int]
    GROWTHGRADE_FIELD_NUMBER: _ClassVar[int]
    MOOD_FIELD_NUMBER: _ClassVar[int]
    GROWTHGP_FIELD_NUMBER: _ClassVar[int]
    GROWTHCOUNT_FIELD_NUMBER: _ClassVar[int]
    FIGHTCAPACITY_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    EQUIPMETS_FIELD_NUMBER: _ClassVar[int]
    EMBLEM_FIELD_NUMBER: _ClassVar[int]
    childId: int
    name: str
    job: int
    sex: int
    userIdA: int
    userIdB: int
    growthGrade: int
    mood: int
    growthGp: int
    growthCount: int
    fightCapacity: int
    state: int
    equipmets: _containers.RepeatedCompositeFieldContainer[ChildEquipmentMsg]
    emblem: int
    def __init__(self, childId: _Optional[int] = ..., name: _Optional[str] = ..., job: _Optional[int] = ..., sex: _Optional[int] = ..., userIdA: _Optional[int] = ..., userIdB: _Optional[int] = ..., growthGrade: _Optional[int] = ..., mood: _Optional[int] = ..., growthGp: _Optional[int] = ..., growthCount: _Optional[int] = ..., fightCapacity: _Optional[int] = ..., state: _Optional[int] = ..., equipmets: _Optional[_Iterable[_Union[ChildEquipmentMsg, _Mapping]]] = ..., emblem: _Optional[int] = ...) -> None: ...

class ClickDataRspMsg(_message.Message):
    __slots__ = ("keys", "keyData", "changeTime")
    KEYS_FIELD_NUMBER: _ClassVar[int]
    KEYDATA_FIELD_NUMBER: _ClassVar[int]
    CHANGETIME_FIELD_NUMBER: _ClassVar[int]
    keys: str
    keyData: int
    changeTime: str
    def __init__(self, keys: _Optional[str] = ..., keyData: _Optional[int] = ..., changeTime: _Optional[str] = ...) -> None: ...

class ClickDatasRspMsg(_message.Message):
    __slots__ = ("info",)
    INFO_FIELD_NUMBER: _ClassVar[int]
    info: _containers.RepeatedCompositeFieldContainer[ClickDataRspMsg]
    def __init__(self, info: _Optional[_Iterable[_Union[ClickDataRspMsg, _Mapping]]] = ...) -> None: ...

class ClientReqMsg(_message.Message):
    __slots__ = ("templateId",)
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    templateId: int
    def __init__(self, templateId: _Optional[int] = ...) -> None: ...

class CollectCampaignNodeMsg(_message.Message):
    __slots__ = ("mastType", "item", "campaignDataId", "sonType", "name")
    MASTTYPE_FIELD_NUMBER: _ClassVar[int]
    ITEM_FIELD_NUMBER: _ClassVar[int]
    CAMPAIGNDATAID_FIELD_NUMBER: _ClassVar[int]
    SONTYPE_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    mastType: int
    item: int
    campaignDataId: int
    sonType: int
    name: str
    def __init__(self, mastType: _Optional[int] = ..., item: _Optional[int] = ..., campaignDataId: _Optional[int] = ..., sonType: _Optional[int] = ..., name: _Optional[str] = ...) -> None: ...

class ComprehendMsg(_message.Message):
    __slots__ = ("templateId",)
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    templateId: int
    def __init__(self, templateId: _Optional[int] = ...) -> None: ...

class ConsortiaAltarOpenReqMsg(_message.Message):
    __slots__ = ("altarType", "waveNum")
    ALTARTYPE_FIELD_NUMBER: _ClassVar[int]
    WAVENUM_FIELD_NUMBER: _ClassVar[int]
    altarType: int
    waveNum: int
    def __init__(self, altarType: _Optional[int] = ..., waveNum: _Optional[int] = ...) -> None: ...

class ConsortiaAltarOpenRspMsg(_message.Message):
    __slots__ = ("consortiaId", "chairmanId", "chairmanName", "result", "altarDate", "pop")
    CONSORTIAID_FIELD_NUMBER: _ClassVar[int]
    CHAIRMANID_FIELD_NUMBER: _ClassVar[int]
    CHAIRMANNAME_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    ALTARDATE_FIELD_NUMBER: _ClassVar[int]
    POP_FIELD_NUMBER: _ClassVar[int]
    consortiaId: int
    chairmanId: int
    chairmanName: str
    result: int
    altarDate: str
    pop: bool
    def __init__(self, consortiaId: _Optional[int] = ..., chairmanId: _Optional[int] = ..., chairmanName: _Optional[str] = ..., result: _Optional[int] = ..., altarDate: _Optional[str] = ..., pop: _Optional[bool] = ...) -> None: ...

class ConsortiaBoxInfoMsg(_message.Message):
    __slots__ = ("templateId", "consortiaId", "count", "addTime", "removeTime")
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    CONSORTIAID_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    ADDTIME_FIELD_NUMBER: _ClassVar[int]
    REMOVETIME_FIELD_NUMBER: _ClassVar[int]
    templateId: int
    consortiaId: int
    count: int
    addTime: bytes
    removeTime: bytes
    def __init__(self, templateId: _Optional[int] = ..., consortiaId: _Optional[int] = ..., count: _Optional[int] = ..., addTime: _Optional[bytes] = ..., removeTime: _Optional[bytes] = ...) -> None: ...

class ConsortiaContributeMsg(_message.Message):
    __slots__ = ("nickName", "totalOffer", "todayOffer")
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    TOTALOFFER_FIELD_NUMBER: _ClassVar[int]
    TODAYOFFER_FIELD_NUMBER: _ClassVar[int]
    nickName: str
    totalOffer: int
    todayOffer: int
    def __init__(self, nickName: _Optional[str] = ..., totalOffer: _Optional[int] = ..., todayOffer: _Optional[int] = ...) -> None: ...

class ConsortiaContributeRspMsg(_message.Message):
    __slots__ = ("totalRows", "contributeInfo", "selfInfo", "selfOrder")
    TOTALROWS_FIELD_NUMBER: _ClassVar[int]
    CONTRIBUTEINFO_FIELD_NUMBER: _ClassVar[int]
    SELFINFO_FIELD_NUMBER: _ClassVar[int]
    SELFORDER_FIELD_NUMBER: _ClassVar[int]
    totalRows: int
    contributeInfo: _containers.RepeatedCompositeFieldContainer[ConsortiaContributeMsg]
    selfInfo: ConsortiaContributeMsg
    selfOrder: int
    def __init__(self, totalRows: _Optional[int] = ..., contributeInfo: _Optional[_Iterable[_Union[ConsortiaContributeMsg, _Mapping]]] = ..., selfInfo: _Optional[_Union[ConsortiaContributeMsg, _Mapping]] = ..., selfOrder: _Optional[int] = ...) -> None: ...

class ConsortiaDutyInfoMsg(_message.Message):
    __slots__ = ("levels", "dutyName", "rights")
    LEVELS_FIELD_NUMBER: _ClassVar[int]
    DUTYNAME_FIELD_NUMBER: _ClassVar[int]
    RIGHTS_FIELD_NUMBER: _ClassVar[int]
    levels: int
    dutyName: str
    rights: bytes
    def __init__(self, levels: _Optional[int] = ..., dutyName: _Optional[str] = ..., rights: _Optional[bytes] = ...) -> None: ...

class ConsortiaDutyListRspMsg(_message.Message):
    __slots__ = ("dutyInfo",)
    DUTYINFO_FIELD_NUMBER: _ClassVar[int]
    dutyInfo: _containers.RepeatedCompositeFieldContainer[ConsortiaDutyInfoMsg]
    def __init__(self, dutyInfo: _Optional[_Iterable[_Union[ConsortiaDutyInfoMsg, _Mapping]]] = ...) -> None: ...

class ConsortiaEventInfoMsg(_message.Message):
    __slots__ = ("id", "consortiaId", "remark", "createDate", "type", "isExist")
    ID_FIELD_NUMBER: _ClassVar[int]
    CONSORTIAID_FIELD_NUMBER: _ClassVar[int]
    REMARK_FIELD_NUMBER: _ClassVar[int]
    CREATEDATE_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    ISEXIST_FIELD_NUMBER: _ClassVar[int]
    id: int
    consortiaId: int
    remark: str
    createDate: str
    type: int
    isExist: bool
    def __init__(self, id: _Optional[int] = ..., consortiaId: _Optional[int] = ..., remark: _Optional[str] = ..., createDate: _Optional[str] = ..., type: _Optional[int] = ..., isExist: _Optional[bool] = ...) -> None: ...

class ConsortiaEventListRspMsg(_message.Message):
    __slots__ = ("eventInfo",)
    EVENTINFO_FIELD_NUMBER: _ClassVar[int]
    eventInfo: _containers.RepeatedCompositeFieldContainer[ConsortiaEventInfoMsg]
    def __init__(self, eventInfo: _Optional[_Iterable[_Union[ConsortiaEventInfoMsg, _Mapping]]] = ...) -> None: ...

class ConsortiaInfoMsg(_message.Message):
    __slots__ = ("consortiaId", "creatorId", "chairmanId", "levels", "addCount", "currentCount", "kickCount", "shopLevel", "storeLevel", "altarLevel", "schoolLevel", "attackLevel", "defenceLevel", "agilityLevel", "abilityLevel", "captainLevel", "goldLevel", "fightPower", "ownWildlands", "offer", "honor", "blessTempId", "blessCount", "codeType", "totalOffer", "op", "placard", "description", "consortiaName", "creatorName", "chairmanName", "renames", "quitResult", "openApp", "isExist", "createDate", "kickDate", "deductDate", "warnDate", "quitDate", "codeBeginDate", "currentDate", "codeNeedDate", "orderInfo", "physiqueLevel", "isRobot", "site", "speakTimes", "votingDate", "votingStatic", "votingId", "activeData", "groupPlacard", "altarDate", "altarState", "maxMave")
    CONSORTIAID_FIELD_NUMBER: _ClassVar[int]
    CREATORID_FIELD_NUMBER: _ClassVar[int]
    CHAIRMANID_FIELD_NUMBER: _ClassVar[int]
    LEVELS_FIELD_NUMBER: _ClassVar[int]
    ADDCOUNT_FIELD_NUMBER: _ClassVar[int]
    CURRENTCOUNT_FIELD_NUMBER: _ClassVar[int]
    KICKCOUNT_FIELD_NUMBER: _ClassVar[int]
    SHOPLEVEL_FIELD_NUMBER: _ClassVar[int]
    STORELEVEL_FIELD_NUMBER: _ClassVar[int]
    ALTARLEVEL_FIELD_NUMBER: _ClassVar[int]
    SCHOOLLEVEL_FIELD_NUMBER: _ClassVar[int]
    ATTACKLEVEL_FIELD_NUMBER: _ClassVar[int]
    DEFENCELEVEL_FIELD_NUMBER: _ClassVar[int]
    AGILITYLEVEL_FIELD_NUMBER: _ClassVar[int]
    ABILITYLEVEL_FIELD_NUMBER: _ClassVar[int]
    CAPTAINLEVEL_FIELD_NUMBER: _ClassVar[int]
    GOLDLEVEL_FIELD_NUMBER: _ClassVar[int]
    FIGHTPOWER_FIELD_NUMBER: _ClassVar[int]
    OWNWILDLANDS_FIELD_NUMBER: _ClassVar[int]
    OFFER_FIELD_NUMBER: _ClassVar[int]
    HONOR_FIELD_NUMBER: _ClassVar[int]
    BLESSTEMPID_FIELD_NUMBER: _ClassVar[int]
    BLESSCOUNT_FIELD_NUMBER: _ClassVar[int]
    CODETYPE_FIELD_NUMBER: _ClassVar[int]
    TOTALOFFER_FIELD_NUMBER: _ClassVar[int]
    OP_FIELD_NUMBER: _ClassVar[int]
    PLACARD_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    CONSORTIANAME_FIELD_NUMBER: _ClassVar[int]
    CREATORNAME_FIELD_NUMBER: _ClassVar[int]
    CHAIRMANNAME_FIELD_NUMBER: _ClassVar[int]
    RENAMES_FIELD_NUMBER: _ClassVar[int]
    QUITRESULT_FIELD_NUMBER: _ClassVar[int]
    OPENAPP_FIELD_NUMBER: _ClassVar[int]
    ISEXIST_FIELD_NUMBER: _ClassVar[int]
    CREATEDATE_FIELD_NUMBER: _ClassVar[int]
    KICKDATE_FIELD_NUMBER: _ClassVar[int]
    DEDUCTDATE_FIELD_NUMBER: _ClassVar[int]
    WARNDATE_FIELD_NUMBER: _ClassVar[int]
    QUITDATE_FIELD_NUMBER: _ClassVar[int]
    CODEBEGINDATE_FIELD_NUMBER: _ClassVar[int]
    CURRENTDATE_FIELD_NUMBER: _ClassVar[int]
    CODENEEDDATE_FIELD_NUMBER: _ClassVar[int]
    ORDERINFO_FIELD_NUMBER: _ClassVar[int]
    PHYSIQUELEVEL_FIELD_NUMBER: _ClassVar[int]
    ISROBOT_FIELD_NUMBER: _ClassVar[int]
    SITE_FIELD_NUMBER: _ClassVar[int]
    SPEAKTIMES_FIELD_NUMBER: _ClassVar[int]
    VOTINGDATE_FIELD_NUMBER: _ClassVar[int]
    VOTINGSTATIC_FIELD_NUMBER: _ClassVar[int]
    VOTINGID_FIELD_NUMBER: _ClassVar[int]
    ACTIVEDATA_FIELD_NUMBER: _ClassVar[int]
    GROUPPLACARD_FIELD_NUMBER: _ClassVar[int]
    ALTARDATE_FIELD_NUMBER: _ClassVar[int]
    ALTARSTATE_FIELD_NUMBER: _ClassVar[int]
    MAXMAVE_FIELD_NUMBER: _ClassVar[int]
    consortiaId: int
    creatorId: int
    chairmanId: int
    levels: int
    addCount: int
    currentCount: int
    kickCount: int
    shopLevel: int
    storeLevel: int
    altarLevel: int
    schoolLevel: int
    attackLevel: int
    defenceLevel: int
    agilityLevel: int
    abilityLevel: int
    captainLevel: int
    goldLevel: int
    fightPower: int
    ownWildlands: int
    offer: int
    honor: int
    blessTempId: int
    blessCount: int
    codeType: int
    totalOffer: int
    op: int
    placard: str
    description: str
    consortiaName: str
    creatorName: str
    chairmanName: str
    renames: str
    quitResult: str
    openApp: bool
    isExist: bool
    createDate: str
    kickDate: str
    deductDate: str
    warnDate: str
    quitDate: str
    codeBeginDate: str
    currentDate: str
    codeNeedDate: int
    orderInfo: ConsortiaOrderInfoMsg
    physiqueLevel: int
    isRobot: bool
    site: _containers.RepeatedScalarFieldContainer[int]
    speakTimes: int
    votingDate: str
    votingStatic: int
    votingId: int
    activeData: int
    groupPlacard: str
    altarDate: str
    altarState: int
    maxMave: int
    def __init__(self, consortiaId: _Optional[int] = ..., creatorId: _Optional[int] = ..., chairmanId: _Optional[int] = ..., levels: _Optional[int] = ..., addCount: _Optional[int] = ..., currentCount: _Optional[int] = ..., kickCount: _Optional[int] = ..., shopLevel: _Optional[int] = ..., storeLevel: _Optional[int] = ..., altarLevel: _Optional[int] = ..., schoolLevel: _Optional[int] = ..., attackLevel: _Optional[int] = ..., defenceLevel: _Optional[int] = ..., agilityLevel: _Optional[int] = ..., abilityLevel: _Optional[int] = ..., captainLevel: _Optional[int] = ..., goldLevel: _Optional[int] = ..., fightPower: _Optional[int] = ..., ownWildlands: _Optional[int] = ..., offer: _Optional[int] = ..., honor: _Optional[int] = ..., blessTempId: _Optional[int] = ..., blessCount: _Optional[int] = ..., codeType: _Optional[int] = ..., totalOffer: _Optional[int] = ..., op: _Optional[int] = ..., placard: _Optional[str] = ..., description: _Optional[str] = ..., consortiaName: _Optional[str] = ..., creatorName: _Optional[str] = ..., chairmanName: _Optional[str] = ..., renames: _Optional[str] = ..., quitResult: _Optional[str] = ..., openApp: _Optional[bool] = ..., isExist: _Optional[bool] = ..., createDate: _Optional[str] = ..., kickDate: _Optional[str] = ..., deductDate: _Optional[str] = ..., warnDate: _Optional[str] = ..., quitDate: _Optional[str] = ..., codeBeginDate: _Optional[str] = ..., currentDate: _Optional[str] = ..., codeNeedDate: _Optional[int] = ..., orderInfo: _Optional[_Union[ConsortiaOrderInfoMsg, _Mapping]] = ..., physiqueLevel: _Optional[int] = ..., isRobot: _Optional[bool] = ..., site: _Optional[_Iterable[int]] = ..., speakTimes: _Optional[int] = ..., votingDate: _Optional[str] = ..., votingStatic: _Optional[int] = ..., votingId: _Optional[int] = ..., activeData: _Optional[int] = ..., groupPlacard: _Optional[str] = ..., altarDate: _Optional[str] = ..., altarState: _Optional[int] = ..., maxMave: _Optional[int] = ...) -> None: ...

class ConsortiaLinkReqMsg(_message.Message):
    __slots__ = ("consortiaId",)
    CONSORTIAID_FIELD_NUMBER: _ClassVar[int]
    consortiaId: int
    def __init__(self, consortiaId: _Optional[int] = ...) -> None: ...

class ConsortiaLinkRspMsg(_message.Message):
    __slots__ = ("consortiaId", "consortiaName", "creatorName", "levels", "offer", "currentCount", "honor", "description")
    CONSORTIAID_FIELD_NUMBER: _ClassVar[int]
    CONSORTIANAME_FIELD_NUMBER: _ClassVar[int]
    CREATORNAME_FIELD_NUMBER: _ClassVar[int]
    LEVELS_FIELD_NUMBER: _ClassVar[int]
    OFFER_FIELD_NUMBER: _ClassVar[int]
    CURRENTCOUNT_FIELD_NUMBER: _ClassVar[int]
    HONOR_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    consortiaId: int
    consortiaName: str
    creatorName: str
    levels: int
    offer: int
    currentCount: int
    honor: int
    description: str
    def __init__(self, consortiaId: _Optional[int] = ..., consortiaName: _Optional[str] = ..., creatorName: _Optional[str] = ..., levels: _Optional[int] = ..., offer: _Optional[int] = ..., currentCount: _Optional[int] = ..., honor: _Optional[int] = ..., description: _Optional[str] = ...) -> None: ...

class ConsortiaMembersInfoMsg(_message.Message):
    __slots__ = ("job", "nickName", "level", "fightCapacity", "userId", "count", "isReceived")
    JOB_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    FIGHTCAPACITY_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    ISRECEIVED_FIELD_NUMBER: _ClassVar[int]
    job: int
    nickName: str
    level: int
    fightCapacity: int
    userId: int
    count: int
    isReceived: bool
    def __init__(self, job: _Optional[int] = ..., nickName: _Optional[str] = ..., level: _Optional[int] = ..., fightCapacity: _Optional[int] = ..., userId: _Optional[int] = ..., count: _Optional[int] = ..., isReceived: _Optional[bool] = ...) -> None: ...

class ConsortiaMsg(_message.Message):
    __slots__ = ("consortiaId", "applyId", "otherId", "contributeGold", "upgradeType", "studySkill", "positionId", "blessSite", "blessTempId", "blessCount", "placard", "description", "consortiaName", "result", "blessLeftTime", "returnItem", "isPay", "groupPlacard", "payType")
    CONSORTIAID_FIELD_NUMBER: _ClassVar[int]
    APPLYID_FIELD_NUMBER: _ClassVar[int]
    OTHERID_FIELD_NUMBER: _ClassVar[int]
    CONTRIBUTEGOLD_FIELD_NUMBER: _ClassVar[int]
    UPGRADETYPE_FIELD_NUMBER: _ClassVar[int]
    STUDYSKILL_FIELD_NUMBER: _ClassVar[int]
    POSITIONID_FIELD_NUMBER: _ClassVar[int]
    BLESSSITE_FIELD_NUMBER: _ClassVar[int]
    BLESSTEMPID_FIELD_NUMBER: _ClassVar[int]
    BLESSCOUNT_FIELD_NUMBER: _ClassVar[int]
    PLACARD_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    CONSORTIANAME_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    BLESSLEFTTIME_FIELD_NUMBER: _ClassVar[int]
    RETURNITEM_FIELD_NUMBER: _ClassVar[int]
    ISPAY_FIELD_NUMBER: _ClassVar[int]
    GROUPPLACARD_FIELD_NUMBER: _ClassVar[int]
    PAYTYPE_FIELD_NUMBER: _ClassVar[int]
    consortiaId: int
    applyId: int
    otherId: int
    contributeGold: int
    upgradeType: int
    studySkill: int
    positionId: int
    blessSite: int
    blessTempId: int
    blessCount: int
    placard: str
    description: str
    consortiaName: str
    result: bool
    blessLeftTime: int
    returnItem: bool
    isPay: bool
    groupPlacard: str
    payType: int
    def __init__(self, consortiaId: _Optional[int] = ..., applyId: _Optional[int] = ..., otherId: _Optional[int] = ..., contributeGold: _Optional[int] = ..., upgradeType: _Optional[int] = ..., studySkill: _Optional[int] = ..., positionId: _Optional[int] = ..., blessSite: _Optional[int] = ..., blessTempId: _Optional[int] = ..., blessCount: _Optional[int] = ..., placard: _Optional[str] = ..., description: _Optional[str] = ..., consortiaName: _Optional[str] = ..., result: _Optional[bool] = ..., blessLeftTime: _Optional[int] = ..., returnItem: _Optional[bool] = ..., isPay: _Optional[bool] = ..., groupPlacard: _Optional[str] = ..., payType: _Optional[int] = ...) -> None: ...

class ConsortiaOfferReqMsg(_message.Message):
    __slots__ = ("pageIndex", "isHistory")
    PAGEINDEX_FIELD_NUMBER: _ClassVar[int]
    ISHISTORY_FIELD_NUMBER: _ClassVar[int]
    pageIndex: int
    isHistory: bool
    def __init__(self, pageIndex: _Optional[int] = ..., isHistory: _Optional[bool] = ...) -> None: ...

class ConsortiaOrderInfoMsg(_message.Message):
    __slots__ = ("consortiaId", "gradeOrder", "fightPowerOrder", "lastDayOffer", "lastDayOrder", "lastWeekOffer", "lastWeekOrder", "offer", "lastDayDate", "lastWeekDate")
    CONSORTIAID_FIELD_NUMBER: _ClassVar[int]
    GRADEORDER_FIELD_NUMBER: _ClassVar[int]
    FIGHTPOWERORDER_FIELD_NUMBER: _ClassVar[int]
    LASTDAYOFFER_FIELD_NUMBER: _ClassVar[int]
    LASTDAYORDER_FIELD_NUMBER: _ClassVar[int]
    LASTWEEKOFFER_FIELD_NUMBER: _ClassVar[int]
    LASTWEEKORDER_FIELD_NUMBER: _ClassVar[int]
    OFFER_FIELD_NUMBER: _ClassVar[int]
    LASTDAYDATE_FIELD_NUMBER: _ClassVar[int]
    LASTWEEKDATE_FIELD_NUMBER: _ClassVar[int]
    consortiaId: int
    gradeOrder: int
    fightPowerOrder: int
    lastDayOffer: int
    lastDayOrder: int
    lastWeekOffer: int
    lastWeekOrder: int
    offer: int
    lastDayDate: str
    lastWeekDate: str
    def __init__(self, consortiaId: _Optional[int] = ..., gradeOrder: _Optional[int] = ..., fightPowerOrder: _Optional[int] = ..., lastDayOffer: _Optional[int] = ..., lastDayOrder: _Optional[int] = ..., lastWeekOffer: _Optional[int] = ..., lastWeekOrder: _Optional[int] = ..., offer: _Optional[int] = ..., lastDayDate: _Optional[str] = ..., lastWeekDate: _Optional[str] = ...) -> None: ...

class ConsortiaQuitReqMsg(_message.Message):
    __slots__ = ("clear_CDType", "payType")
    CLEAR_CDTYPE_FIELD_NUMBER: _ClassVar[int]
    PAYTYPE_FIELD_NUMBER: _ClassVar[int]
    clear_CDType: int
    payType: int
    def __init__(self, clear_CDType: _Optional[int] = ..., payType: _Optional[int] = ...) -> None: ...

class ConsortiaRenameReqMsg(_message.Message):
    __slots__ = ("same", "newName", "payType")
    SAME_FIELD_NUMBER: _ClassVar[int]
    NEWNAME_FIELD_NUMBER: _ClassVar[int]
    PAYTYPE_FIELD_NUMBER: _ClassVar[int]
    same: bool
    newName: str
    payType: int
    def __init__(self, same: _Optional[bool] = ..., newName: _Optional[str] = ..., payType: _Optional[int] = ...) -> None: ...

class ConsortiaRenameRspMsg(_message.Message):
    __slots__ = ("result",)
    RESULT_FIELD_NUMBER: _ClassVar[int]
    result: bool
    def __init__(self, result: _Optional[bool] = ...) -> None: ...

class ConsortiaSearchRspMsg(_message.Message):
    __slots__ = ("totalRows", "consortiaInfo", "isReset")
    TOTALROWS_FIELD_NUMBER: _ClassVar[int]
    CONSORTIAINFO_FIELD_NUMBER: _ClassVar[int]
    ISRESET_FIELD_NUMBER: _ClassVar[int]
    totalRows: int
    consortiaInfo: _containers.RepeatedCompositeFieldContainer[ConsortiaInfoMsg]
    isReset: bool
    def __init__(self, totalRows: _Optional[int] = ..., consortiaInfo: _Optional[_Iterable[_Union[ConsortiaInfoMsg, _Mapping]]] = ..., isReset: _Optional[bool] = ...) -> None: ...

class ConsortiaStorageInfoMsg(_message.Message):
    __slots__ = ("storageInfo",)
    STORAGEINFO_FIELD_NUMBER: _ClassVar[int]
    storageInfo: _containers.RepeatedCompositeFieldContainer[ConsortiaBoxInfoMsg]
    def __init__(self, storageInfo: _Optional[_Iterable[_Union[ConsortiaBoxInfoMsg, _Mapping]]] = ...) -> None: ...

class ConsortiaTreasureBoxMsg(_message.Message):
    __slots__ = ("consortiaId", "chairmanId", "templateId", "count", "playerInfo")
    CONSORTIAID_FIELD_NUMBER: _ClassVar[int]
    CHAIRMANID_FIELD_NUMBER: _ClassVar[int]
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    PLAYERINFO_FIELD_NUMBER: _ClassVar[int]
    consortiaId: int
    chairmanId: int
    templateId: int
    count: int
    playerInfo: _containers.RepeatedCompositeFieldContainer[ConsortiaMembersInfoMsg]
    def __init__(self, consortiaId: _Optional[int] = ..., chairmanId: _Optional[int] = ..., templateId: _Optional[int] = ..., count: _Optional[int] = ..., playerInfo: _Optional[_Iterable[_Union[ConsortiaMembersInfoMsg, _Mapping]]] = ...) -> None: ...

class ConsortiaUserInviteInfoListRspMsg(_message.Message):
    __slots__ = ("inviteInfo",)
    INVITEINFO_FIELD_NUMBER: _ClassVar[int]
    inviteInfo: _containers.RepeatedCompositeFieldContainer[ConsortiaUserInviteInfoMsg]
    def __init__(self, inviteInfo: _Optional[_Iterable[_Union[ConsortiaUserInviteInfoMsg, _Mapping]]] = ...) -> None: ...

class ConsortiaUserInviteInfoMsg(_message.Message):
    __slots__ = ("id", "consortiaId", "consortiaName", "createDate", "userId", "userNickname", "inviteId", "inviteNickname", "chairmanNickname", "inviteDate", "fromType", "isexist")
    ID_FIELD_NUMBER: _ClassVar[int]
    CONSORTIAID_FIELD_NUMBER: _ClassVar[int]
    CONSORTIANAME_FIELD_NUMBER: _ClassVar[int]
    CREATEDATE_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    USERNICKNAME_FIELD_NUMBER: _ClassVar[int]
    INVITEID_FIELD_NUMBER: _ClassVar[int]
    INVITENICKNAME_FIELD_NUMBER: _ClassVar[int]
    CHAIRMANNICKNAME_FIELD_NUMBER: _ClassVar[int]
    INVITEDATE_FIELD_NUMBER: _ClassVar[int]
    FROMTYPE_FIELD_NUMBER: _ClassVar[int]
    ISEXIST_FIELD_NUMBER: _ClassVar[int]
    id: int
    consortiaId: int
    consortiaName: str
    createDate: str
    userId: int
    userNickname: str
    inviteId: int
    inviteNickname: str
    chairmanNickname: str
    inviteDate: str
    fromType: bool
    isexist: bool
    def __init__(self, id: _Optional[int] = ..., consortiaId: _Optional[int] = ..., consortiaName: _Optional[str] = ..., createDate: _Optional[str] = ..., userId: _Optional[int] = ..., userNickname: _Optional[str] = ..., inviteId: _Optional[int] = ..., inviteNickname: _Optional[str] = ..., chairmanNickname: _Optional[str] = ..., inviteDate: _Optional[str] = ..., fromType: _Optional[bool] = ..., isexist: _Optional[bool] = ...) -> None: ...

class ConsortiaUserOfferReqMsg(_message.Message):
    __slots__ = ("offerGold", "offerPoint", "payType")
    OFFERGOLD_FIELD_NUMBER: _ClassVar[int]
    OFFERPOINT_FIELD_NUMBER: _ClassVar[int]
    PAYTYPE_FIELD_NUMBER: _ClassVar[int]
    offerGold: int
    offerPoint: int
    payType: int
    def __init__(self, offerGold: _Optional[int] = ..., offerPoint: _Optional[int] = ..., payType: _Optional[int] = ...) -> None: ...

class ConsortiaVotingRspMsg(_message.Message):
    __slots__ = ("result",)
    RESULT_FIELD_NUMBER: _ClassVar[int]
    result: bool
    def __init__(self, result: _Optional[bool] = ...) -> None: ...

class ConsortiaVotingUserMsg(_message.Message):
    __slots__ = ("userId", "nickName", "votingId", "isVotingman", "votingTime", "votingData")
    USERID_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    VOTINGID_FIELD_NUMBER: _ClassVar[int]
    ISVOTINGMAN_FIELD_NUMBER: _ClassVar[int]
    VOTINGTIME_FIELD_NUMBER: _ClassVar[int]
    VOTINGDATA_FIELD_NUMBER: _ClassVar[int]
    userId: int
    nickName: str
    votingId: int
    isVotingman: bool
    votingTime: int
    votingData: int
    def __init__(self, userId: _Optional[int] = ..., nickName: _Optional[str] = ..., votingId: _Optional[int] = ..., isVotingman: _Optional[bool] = ..., votingTime: _Optional[int] = ..., votingData: _Optional[int] = ...) -> None: ...

class ConsortiaVotingUsersMsg(_message.Message):
    __slots__ = ("info",)
    INFO_FIELD_NUMBER: _ClassVar[int]
    info: _containers.RepeatedCompositeFieldContainer[ConsortiaVotingUserMsg]
    def __init__(self, info: _Optional[_Iterable[_Union[ConsortiaVotingUserMsg, _Mapping]]] = ...) -> None: ...

class ConsumeInfoMsg(_message.Message):
    __slots__ = ("userId", "order", "point", "nickName", "isVip")
    USERID_FIELD_NUMBER: _ClassVar[int]
    ORDER_FIELD_NUMBER: _ClassVar[int]
    POINT_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    ISVIP_FIELD_NUMBER: _ClassVar[int]
    userId: int
    order: int
    point: int
    nickName: str
    isVip: bool
    def __init__(self, userId: _Optional[int] = ..., order: _Optional[int] = ..., point: _Optional[int] = ..., nickName: _Optional[str] = ..., isVip: _Optional[bool] = ...) -> None: ...

class CoolDownMsg(_message.Message):
    __slots__ = ("templatedId", "coolDown", "coolType", "appearCoolDown")
    TEMPLATEDID_FIELD_NUMBER: _ClassVar[int]
    COOLDOWN_FIELD_NUMBER: _ClassVar[int]
    COOLTYPE_FIELD_NUMBER: _ClassVar[int]
    APPEARCOOLDOWN_FIELD_NUMBER: _ClassVar[int]
    templatedId: int
    coolDown: int
    coolType: int
    appearCoolDown: int
    def __init__(self, templatedId: _Optional[int] = ..., coolDown: _Optional[int] = ..., coolType: _Optional[int] = ..., appearCoolDown: _Optional[int] = ...) -> None: ...

class CrazyFishInfoMsg(_message.Message):
    __slots__ = ("fishId", "angle", "frame")
    FISHID_FIELD_NUMBER: _ClassVar[int]
    ANGLE_FIELD_NUMBER: _ClassVar[int]
    FRAME_FIELD_NUMBER: _ClassVar[int]
    fishId: int
    angle: int
    frame: int
    def __init__(self, fishId: _Optional[int] = ..., angle: _Optional[int] = ..., frame: _Optional[int] = ...) -> None: ...

class CrossArmyListMsg(_message.Message):
    __slots__ = ("armyList",)
    ARMYLIST_FIELD_NUMBER: _ClassVar[int]
    armyList: _containers.RepeatedCompositeFieldContainer[CrossArmyMsg]
    def __init__(self, armyList: _Optional[_Iterable[_Union[CrossArmyMsg, _Mapping]]] = ...) -> None: ...

class CrossArmyMsg(_message.Message):
    __slots__ = ("armyId", "playerId", "curPosX", "curPosY", "state", "serverName")
    ARMYID_FIELD_NUMBER: _ClassVar[int]
    PLAYERID_FIELD_NUMBER: _ClassVar[int]
    CURPOSX_FIELD_NUMBER: _ClassVar[int]
    CURPOSY_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    armyId: int
    playerId: int
    curPosX: int
    curPosY: int
    state: int
    serverName: str
    def __init__(self, armyId: _Optional[int] = ..., playerId: _Optional[int] = ..., curPosX: _Optional[int] = ..., curPosY: _Optional[int] = ..., state: _Optional[int] = ..., serverName: _Optional[str] = ...) -> None: ...

class CrossBigBugleMsg(_message.Message):
    __slots__ = ("serverId", "serverName", "uid", "userId", "nickName", "isLookInfo", "content", "param1", "param2")
    SERVERID_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    UID_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    ISLOOKINFO_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    PARAM1_FIELD_NUMBER: _ClassVar[int]
    PARAM2_FIELD_NUMBER: _ClassVar[int]
    serverId: int
    serverName: str
    uid: str
    userId: int
    nickName: str
    isLookInfo: bool
    content: str
    param1: int
    param2: str
    def __init__(self, serverId: _Optional[int] = ..., serverName: _Optional[str] = ..., uid: _Optional[str] = ..., userId: _Optional[int] = ..., nickName: _Optional[str] = ..., isLookInfo: _Optional[bool] = ..., content: _Optional[str] = ..., param1: _Optional[int] = ..., param2: _Optional[str] = ...) -> None: ...

class CrossGuildMsg(_message.Message):
    __slots__ = ("eventType", "info", "param1", "param2", "param3", "param4", "param5", "param6", "propertys1", "propertys2", "param7", "isOver", "totalCount", "uuid", "curNum", "totalNum")
    EVENTTYPE_FIELD_NUMBER: _ClassVar[int]
    INFO_FIELD_NUMBER: _ClassVar[int]
    PARAM1_FIELD_NUMBER: _ClassVar[int]
    PARAM2_FIELD_NUMBER: _ClassVar[int]
    PARAM3_FIELD_NUMBER: _ClassVar[int]
    PARAM4_FIELD_NUMBER: _ClassVar[int]
    PARAM5_FIELD_NUMBER: _ClassVar[int]
    PARAM6_FIELD_NUMBER: _ClassVar[int]
    PROPERTYS1_FIELD_NUMBER: _ClassVar[int]
    PROPERTYS2_FIELD_NUMBER: _ClassVar[int]
    PARAM7_FIELD_NUMBER: _ClassVar[int]
    ISOVER_FIELD_NUMBER: _ClassVar[int]
    TOTALCOUNT_FIELD_NUMBER: _ClassVar[int]
    UUID_FIELD_NUMBER: _ClassVar[int]
    CURNUM_FIELD_NUMBER: _ClassVar[int]
    TOTALNUM_FIELD_NUMBER: _ClassVar[int]
    eventType: int
    info: _containers.RepeatedCompositeFieldContainer[GuildInfoMsg]
    param1: int
    param2: int
    param3: int
    param4: str
    param5: str
    param6: str
    propertys1: _containers.RepeatedScalarFieldContainer[int]
    propertys2: _containers.RepeatedScalarFieldContainer[str]
    param7: str
    isOver: bool
    totalCount: int
    uuid: str
    curNum: int
    totalNum: int
    def __init__(self, eventType: _Optional[int] = ..., info: _Optional[_Iterable[_Union[GuildInfoMsg, _Mapping]]] = ..., param1: _Optional[int] = ..., param2: _Optional[int] = ..., param3: _Optional[int] = ..., param4: _Optional[str] = ..., param5: _Optional[str] = ..., param6: _Optional[str] = ..., propertys1: _Optional[_Iterable[int]] = ..., propertys2: _Optional[_Iterable[str]] = ..., param7: _Optional[str] = ..., isOver: _Optional[bool] = ..., totalCount: _Optional[int] = ..., uuid: _Optional[str] = ..., curNum: _Optional[int] = ..., totalNum: _Optional[int] = ...) -> None: ...

class CrossVehicleAttackReqMsg(_message.Message):
    __slots__ = ("skillId", "attackType", "suffererNpcId", "suffererId", "suffererServerName", "effectX", "effectY")
    SKILLID_FIELD_NUMBER: _ClassVar[int]
    ATTACKTYPE_FIELD_NUMBER: _ClassVar[int]
    SUFFERERNPCID_FIELD_NUMBER: _ClassVar[int]
    SUFFERERID_FIELD_NUMBER: _ClassVar[int]
    SUFFERERSERVERNAME_FIELD_NUMBER: _ClassVar[int]
    EFFECTX_FIELD_NUMBER: _ClassVar[int]
    EFFECTY_FIELD_NUMBER: _ClassVar[int]
    skillId: int
    attackType: int
    suffererNpcId: _containers.RepeatedScalarFieldContainer[int]
    suffererId: _containers.RepeatedScalarFieldContainer[int]
    suffererServerName: _containers.RepeatedScalarFieldContainer[str]
    effectX: int
    effectY: int
    def __init__(self, skillId: _Optional[int] = ..., attackType: _Optional[int] = ..., suffererNpcId: _Optional[_Iterable[int]] = ..., suffererId: _Optional[_Iterable[int]] = ..., suffererServerName: _Optional[_Iterable[str]] = ..., effectX: _Optional[int] = ..., effectY: _Optional[int] = ...) -> None: ...

class DamageMsg(_message.Message):
    __slots__ = ("livingId", "damageType", "hasIcon", "isHarmful", "damageValue", "leftValue", "extraData", "parry", "dropInfos", "order", "hpLimit", "resistValue", "resistType")
    LIVINGID_FIELD_NUMBER: _ClassVar[int]
    DAMAGETYPE_FIELD_NUMBER: _ClassVar[int]
    HASICON_FIELD_NUMBER: _ClassVar[int]
    ISHARMFUL_FIELD_NUMBER: _ClassVar[int]
    DAMAGEVALUE_FIELD_NUMBER: _ClassVar[int]
    LEFTVALUE_FIELD_NUMBER: _ClassVar[int]
    EXTRADATA_FIELD_NUMBER: _ClassVar[int]
    PARRY_FIELD_NUMBER: _ClassVar[int]
    DROPINFOS_FIELD_NUMBER: _ClassVar[int]
    ORDER_FIELD_NUMBER: _ClassVar[int]
    HPLIMIT_FIELD_NUMBER: _ClassVar[int]
    RESISTVALUE_FIELD_NUMBER: _ClassVar[int]
    RESISTTYPE_FIELD_NUMBER: _ClassVar[int]
    livingId: int
    damageType: int
    hasIcon: bool
    isHarmful: bool
    damageValue: int
    leftValue: int
    extraData: int
    parry: bool
    dropInfos: _containers.RepeatedCompositeFieldContainer[DropInfoMsg]
    order: int
    hpLimit: int
    resistValue: int
    resistType: int
    def __init__(self, livingId: _Optional[int] = ..., damageType: _Optional[int] = ..., hasIcon: _Optional[bool] = ..., isHarmful: _Optional[bool] = ..., damageValue: _Optional[int] = ..., leftValue: _Optional[int] = ..., extraData: _Optional[int] = ..., parry: _Optional[bool] = ..., dropInfos: _Optional[_Iterable[_Union[DropInfoMsg, _Mapping]]] = ..., order: _Optional[int] = ..., hpLimit: _Optional[int] = ..., resistValue: _Optional[int] = ..., resistType: _Optional[int] = ...) -> None: ...

class DataResetMsg(_message.Message):
    __slots__ = ("weary", "hangupCount", "transEnergy", "attackCount", "challengeCount", "leftHangupWeary", "tower1EnterCount", "tower2EnterCount", "blessingCount", "blessingBuff", "buyCount", "king_Buff", "serverName", "upRuneByPointTimes")
    WEARY_FIELD_NUMBER: _ClassVar[int]
    HANGUPCOUNT_FIELD_NUMBER: _ClassVar[int]
    TRANSENERGY_FIELD_NUMBER: _ClassVar[int]
    ATTACKCOUNT_FIELD_NUMBER: _ClassVar[int]
    CHALLENGECOUNT_FIELD_NUMBER: _ClassVar[int]
    LEFTHANGUPWEARY_FIELD_NUMBER: _ClassVar[int]
    TOWER1ENTERCOUNT_FIELD_NUMBER: _ClassVar[int]
    TOWER2ENTERCOUNT_FIELD_NUMBER: _ClassVar[int]
    BLESSINGCOUNT_FIELD_NUMBER: _ClassVar[int]
    BLESSINGBUFF_FIELD_NUMBER: _ClassVar[int]
    BUYCOUNT_FIELD_NUMBER: _ClassVar[int]
    KING_BUFF_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    UPRUNEBYPOINTTIMES_FIELD_NUMBER: _ClassVar[int]
    weary: int
    hangupCount: int
    transEnergy: int
    attackCount: int
    challengeCount: int
    leftHangupWeary: int
    tower1EnterCount: int
    tower2EnterCount: int
    blessingCount: int
    blessingBuff: int
    buyCount: int
    king_Buff: bool
    serverName: str
    upRuneByPointTimes: int
    def __init__(self, weary: _Optional[int] = ..., hangupCount: _Optional[int] = ..., transEnergy: _Optional[int] = ..., attackCount: _Optional[int] = ..., challengeCount: _Optional[int] = ..., leftHangupWeary: _Optional[int] = ..., tower1EnterCount: _Optional[int] = ..., tower2EnterCount: _Optional[int] = ..., blessingCount: _Optional[int] = ..., blessingBuff: _Optional[int] = ..., buyCount: _Optional[int] = ..., king_Buff: _Optional[bool] = ..., serverName: _Optional[str] = ..., upRuneByPointTimes: _Optional[int] = ...) -> None: ...

class DayActiveRspInfo(_message.Message):
    __slots__ = ("activeId", "title", "description", "contents", "awardContent", "startDate", "endDate", "actionTimeContent", "sort")
    ACTIVEID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    CONTENTS_FIELD_NUMBER: _ClassVar[int]
    AWARDCONTENT_FIELD_NUMBER: _ClassVar[int]
    STARTDATE_FIELD_NUMBER: _ClassVar[int]
    ENDDATE_FIELD_NUMBER: _ClassVar[int]
    ACTIONTIMECONTENT_FIELD_NUMBER: _ClassVar[int]
    SORT_FIELD_NUMBER: _ClassVar[int]
    activeId: str
    title: str
    description: str
    contents: str
    awardContent: str
    startDate: str
    endDate: str
    actionTimeContent: str
    sort: int
    def __init__(self, activeId: _Optional[str] = ..., title: _Optional[str] = ..., description: _Optional[str] = ..., contents: _Optional[str] = ..., awardContent: _Optional[str] = ..., startDate: _Optional[str] = ..., endDate: _Optional[str] = ..., actionTimeContent: _Optional[str] = ..., sort: _Optional[int] = ...) -> None: ...

class DayActiveRspMsg(_message.Message):
    __slots__ = ("dayActiveRspInfo",)
    DAYACTIVERSPINFO_FIELD_NUMBER: _ClassVar[int]
    dayActiveRspInfo: _containers.RepeatedCompositeFieldContainer[DayActiveRspInfo]
    def __init__(self, dayActiveRspInfo: _Optional[_Iterable[_Union[DayActiveRspInfo, _Mapping]]] = ...) -> None: ...

class DepositActiveMsg(_message.Message):
    __slots__ = ("activeId", "title", "contents", "activeType", "description", "actionTimeContent", "consortia", "grades", "setStartDate", "setEndDate", "getStartDate", "getEndDate", "depositLevel", "depositTime", "opType", "opParam", "harvestedInfos", "activeParams", "logs")
    ACTIVEID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    CONTENTS_FIELD_NUMBER: _ClassVar[int]
    ACTIVETYPE_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    ACTIONTIMECONTENT_FIELD_NUMBER: _ClassVar[int]
    CONSORTIA_FIELD_NUMBER: _ClassVar[int]
    GRADES_FIELD_NUMBER: _ClassVar[int]
    SETSTARTDATE_FIELD_NUMBER: _ClassVar[int]
    SETENDDATE_FIELD_NUMBER: _ClassVar[int]
    GETSTARTDATE_FIELD_NUMBER: _ClassVar[int]
    GETENDDATE_FIELD_NUMBER: _ClassVar[int]
    DEPOSITLEVEL_FIELD_NUMBER: _ClassVar[int]
    DEPOSITTIME_FIELD_NUMBER: _ClassVar[int]
    OPTYPE_FIELD_NUMBER: _ClassVar[int]
    OPPARAM_FIELD_NUMBER: _ClassVar[int]
    HARVESTEDINFOS_FIELD_NUMBER: _ClassVar[int]
    ACTIVEPARAMS_FIELD_NUMBER: _ClassVar[int]
    LOGS_FIELD_NUMBER: _ClassVar[int]
    activeId: str
    title: str
    contents: str
    activeType: int
    description: str
    actionTimeContent: int
    consortia: int
    grades: int
    setStartDate: str
    setEndDate: str
    getStartDate: str
    getEndDate: str
    depositLevel: int
    depositTime: str
    opType: int
    opParam: int
    harvestedInfos: _containers.RepeatedCompositeFieldContainer[GItemInfoMsg]
    activeParams: _containers.RepeatedCompositeFieldContainer[ActiveParamMsg]
    logs: _containers.RepeatedCompositeFieldContainer[GetLogMsg]
    def __init__(self, activeId: _Optional[str] = ..., title: _Optional[str] = ..., contents: _Optional[str] = ..., activeType: _Optional[int] = ..., description: _Optional[str] = ..., actionTimeContent: _Optional[int] = ..., consortia: _Optional[int] = ..., grades: _Optional[int] = ..., setStartDate: _Optional[str] = ..., setEndDate: _Optional[str] = ..., getStartDate: _Optional[str] = ..., getEndDate: _Optional[str] = ..., depositLevel: _Optional[int] = ..., depositTime: _Optional[str] = ..., opType: _Optional[int] = ..., opParam: _Optional[int] = ..., harvestedInfos: _Optional[_Iterable[_Union[GItemInfoMsg, _Mapping]]] = ..., activeParams: _Optional[_Iterable[_Union[ActiveParamMsg, _Mapping]]] = ..., logs: _Optional[_Iterable[_Union[GetLogMsg, _Mapping]]] = ...) -> None: ...

class DetailReqMsg(_message.Message):
    __slots__ = ("userId", "serverName", "otherId", "otherName", "itemInfo", "armyInfo", "heroInfo", "pawnInfo")
    USERID_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    OTHERID_FIELD_NUMBER: _ClassVar[int]
    OTHERNAME_FIELD_NUMBER: _ClassVar[int]
    ITEMINFO_FIELD_NUMBER: _ClassVar[int]
    ARMYINFO_FIELD_NUMBER: _ClassVar[int]
    HEROINFO_FIELD_NUMBER: _ClassVar[int]
    PAWNINFO_FIELD_NUMBER: _ClassVar[int]
    userId: int
    serverName: str
    otherId: int
    otherName: str
    itemInfo: bool
    armyInfo: bool
    heroInfo: bool
    pawnInfo: bool
    def __init__(self, userId: _Optional[int] = ..., serverName: _Optional[str] = ..., otherId: _Optional[int] = ..., otherName: _Optional[str] = ..., itemInfo: _Optional[bool] = ..., armyInfo: _Optional[bool] = ..., heroInfo: _Optional[bool] = ..., pawnInfo: _Optional[bool] = ...) -> None: ...

class DetailRspMsg(_message.Message):
    __slots__ = ("otherId", "serverName", "item", "army", "star", "hideFashion", "watch", "powcardfight")
    OTHERID_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    ITEM_FIELD_NUMBER: _ClassVar[int]
    ARMY_FIELD_NUMBER: _ClassVar[int]
    STAR_FIELD_NUMBER: _ClassVar[int]
    HIDEFASHION_FIELD_NUMBER: _ClassVar[int]
    WATCH_FIELD_NUMBER: _ClassVar[int]
    POWCARDFIGHT_FIELD_NUMBER: _ClassVar[int]
    otherId: int
    serverName: str
    item: _containers.RepeatedCompositeFieldContainer[SimpleItemInfoMsg]
    army: SimpleArmyMsg
    star: _containers.RepeatedCompositeFieldContainer[SimpleStarInfoMsg]
    hideFashion: bool
    watch: _containers.RepeatedCompositeFieldContainer[SimpleWatchMsg]
    powcardfight: _containers.RepeatedCompositeFieldContainer[SimplePowCardFightInfoMsg]
    def __init__(self, otherId: _Optional[int] = ..., serverName: _Optional[str] = ..., item: _Optional[_Iterable[_Union[SimpleItemInfoMsg, _Mapping]]] = ..., army: _Optional[_Union[SimpleArmyMsg, _Mapping]] = ..., star: _Optional[_Iterable[_Union[SimpleStarInfoMsg, _Mapping]]] = ..., hideFashion: _Optional[bool] = ..., watch: _Optional[_Iterable[_Union[SimpleWatchMsg, _Mapping]]] = ..., powcardfight: _Optional[_Iterable[_Union[SimplePowCardFightInfoMsg, _Mapping]]] = ...) -> None: ...

class DropInfoMsg(_message.Message):
    __slots__ = ("dropId", "dropCount", "winnerIds", "param1", "param2")
    DROPID_FIELD_NUMBER: _ClassVar[int]
    DROPCOUNT_FIELD_NUMBER: _ClassVar[int]
    WINNERIDS_FIELD_NUMBER: _ClassVar[int]
    PARAM1_FIELD_NUMBER: _ClassVar[int]
    PARAM2_FIELD_NUMBER: _ClassVar[int]
    dropId: int
    dropCount: int
    winnerIds: _containers.RepeatedScalarFieldContainer[int]
    param1: int
    param2: int
    def __init__(self, dropId: _Optional[int] = ..., dropCount: _Optional[int] = ..., winnerIds: _Optional[_Iterable[int]] = ..., param1: _Optional[int] = ..., param2: _Optional[int] = ...) -> None: ...

class EditRoomRspMsg(_message.Message):
    __slots__ = ("roomId", "startCampaignId", "masterId", "count", "capacity", "passWord", "roomName")
    ROOMID_FIELD_NUMBER: _ClassVar[int]
    STARTCAMPAIGNID_FIELD_NUMBER: _ClassVar[int]
    MASTERID_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    CAPACITY_FIELD_NUMBER: _ClassVar[int]
    PASSWORD_FIELD_NUMBER: _ClassVar[int]
    ROOMNAME_FIELD_NUMBER: _ClassVar[int]
    roomId: int
    startCampaignId: int
    masterId: int
    count: int
    capacity: int
    passWord: str
    roomName: str
    def __init__(self, roomId: _Optional[int] = ..., startCampaignId: _Optional[int] = ..., masterId: _Optional[int] = ..., count: _Optional[int] = ..., capacity: _Optional[int] = ..., passWord: _Optional[str] = ..., roomName: _Optional[str] = ...) -> None: ...

class EffectRemoveReqMsg(_message.Message):
    __slots__ = ("templateId",)
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    templateId: int
    def __init__(self, templateId: _Optional[int] = ...) -> None: ...

class EngageMsg(_message.Message):
    __slots__ = ("engageInfos",)
    ENGAGEINFOS_FIELD_NUMBER: _ClassVar[int]
    engageInfos: _containers.RepeatedCompositeFieldContainer[MarriageProMsg]
    def __init__(self, engageInfos: _Optional[_Iterable[_Union[MarriageProMsg, _Mapping]]] = ...) -> None: ...

class EquipLookDataMsg(_message.Message):
    __slots__ = ("otherId", "item")
    OTHERID_FIELD_NUMBER: _ClassVar[int]
    ITEM_FIELD_NUMBER: _ClassVar[int]
    otherId: int
    item: _containers.RepeatedCompositeFieldContainer[ItemInfoMsg]
    def __init__(self, otherId: _Optional[int] = ..., item: _Optional[_Iterable[_Union[ItemInfoMsg, _Mapping]]] = ...) -> None: ...

class EquipLookMsg(_message.Message):
    __slots__ = ("otherId",)
    OTHERID_FIELD_NUMBER: _ClassVar[int]
    otherId: int
    def __init__(self, otherId: _Optional[int] = ...) -> None: ...

class ExchangeActive(_message.Message):
    __slots__ = ("startTime", "endTime", "bagId", "bagName", "rewardItem", "needItem")
    STARTTIME_FIELD_NUMBER: _ClassVar[int]
    ENDTIME_FIELD_NUMBER: _ClassVar[int]
    BAGID_FIELD_NUMBER: _ClassVar[int]
    BAGNAME_FIELD_NUMBER: _ClassVar[int]
    REWARDITEM_FIELD_NUMBER: _ClassVar[int]
    NEEDITEM_FIELD_NUMBER: _ClassVar[int]
    startTime: str
    endTime: str
    bagId: int
    bagName: str
    rewardItem: _containers.RepeatedCompositeFieldContainer[ExchangeItemInfo]
    needItem: _containers.RepeatedCompositeFieldContainer[ExchangeItemInfo]
    def __init__(self, startTime: _Optional[str] = ..., endTime: _Optional[str] = ..., bagId: _Optional[int] = ..., bagName: _Optional[str] = ..., rewardItem: _Optional[_Iterable[_Union[ExchangeItemInfo, _Mapping]]] = ..., needItem: _Optional[_Iterable[_Union[ExchangeItemInfo, _Mapping]]] = ...) -> None: ...

class ExchangeItemInfo(_message.Message):
    __slots__ = ("templateId", "count")
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    templateId: int
    count: int
    def __init__(self, templateId: _Optional[int] = ..., count: _Optional[int] = ...) -> None: ...

class ExchangeMsg(_message.Message):
    __slots__ = ("activeInfo",)
    ACTIVEINFO_FIELD_NUMBER: _ClassVar[int]
    activeInfo: _containers.RepeatedCompositeFieldContainer[ExchangeActive]
    def __init__(self, activeInfo: _Optional[_Iterable[_Union[ExchangeActive, _Mapping]]] = ...) -> None: ...

class ExchangeReq(_message.Message):
    __slots__ = ("bagId",)
    BAGID_FIELD_NUMBER: _ClassVar[int]
    bagId: int
    def __init__(self, bagId: _Optional[int] = ...) -> None: ...

class FamInfoMsg(_message.Message):
    __slots__ = ("consortiaId", "treeGrades", "treeGp", "treeWaterCount", "treeState", "personNum", "rate", "opreate", "userId", "pickTime")
    CONSORTIAID_FIELD_NUMBER: _ClassVar[int]
    TREEGRADES_FIELD_NUMBER: _ClassVar[int]
    TREEGP_FIELD_NUMBER: _ClassVar[int]
    TREEWATERCOUNT_FIELD_NUMBER: _ClassVar[int]
    TREESTATE_FIELD_NUMBER: _ClassVar[int]
    PERSONNUM_FIELD_NUMBER: _ClassVar[int]
    RATE_FIELD_NUMBER: _ClassVar[int]
    OPREATE_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    PICKTIME_FIELD_NUMBER: _ClassVar[int]
    consortiaId: int
    treeGrades: int
    treeGp: int
    treeWaterCount: int
    treeState: int
    personNum: int
    rate: float
    opreate: int
    userId: _containers.RepeatedScalarFieldContainer[int]
    pickTime: str
    def __init__(self, consortiaId: _Optional[int] = ..., treeGrades: _Optional[int] = ..., treeGp: _Optional[int] = ..., treeWaterCount: _Optional[int] = ..., treeState: _Optional[int] = ..., personNum: _Optional[int] = ..., rate: _Optional[float] = ..., opreate: _Optional[int] = ..., userId: _Optional[_Iterable[int]] = ..., pickTime: _Optional[str] = ...) -> None: ...

class FamLordsInfoMsg(_message.Message):
    __slots__ = ("isCanCall", "order", "expairtDate", "isOpenLordsNode", "currentTurns", "leftTime", "userIds")
    ISCANCALL_FIELD_NUMBER: _ClassVar[int]
    ORDER_FIELD_NUMBER: _ClassVar[int]
    EXPAIRTDATE_FIELD_NUMBER: _ClassVar[int]
    ISOPENLORDSNODE_FIELD_NUMBER: _ClassVar[int]
    CURRENTTURNS_FIELD_NUMBER: _ClassVar[int]
    LEFTTIME_FIELD_NUMBER: _ClassVar[int]
    USERIDS_FIELD_NUMBER: _ClassVar[int]
    isCanCall: bool
    order: int
    expairtDate: str
    isOpenLordsNode: bool
    currentTurns: int
    leftTime: int
    userIds: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, isCanCall: _Optional[bool] = ..., order: _Optional[int] = ..., expairtDate: _Optional[str] = ..., isOpenLordsNode: _Optional[bool] = ..., currentTurns: _Optional[int] = ..., leftTime: _Optional[int] = ..., userIds: _Optional[_Iterable[int]] = ...) -> None: ...

class FarmInfoRspMsg(_message.Message):
    __slots__ = ("userId", "nickName", "grades", "landGrades", "gp", "totalGp", "todayFromFriendGp", "farmLandInfo", "treeInfo", "todayStolenCount", "petInfo", "guardPetInfo", "marriageTree")
    USERID_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    GRADES_FIELD_NUMBER: _ClassVar[int]
    LANDGRADES_FIELD_NUMBER: _ClassVar[int]
    GP_FIELD_NUMBER: _ClassVar[int]
    TOTALGP_FIELD_NUMBER: _ClassVar[int]
    TODAYFROMFRIENDGP_FIELD_NUMBER: _ClassVar[int]
    FARMLANDINFO_FIELD_NUMBER: _ClassVar[int]
    TREEINFO_FIELD_NUMBER: _ClassVar[int]
    TODAYSTOLENCOUNT_FIELD_NUMBER: _ClassVar[int]
    PETINFO_FIELD_NUMBER: _ClassVar[int]
    GUARDPETINFO_FIELD_NUMBER: _ClassVar[int]
    MARRIAGETREE_FIELD_NUMBER: _ClassVar[int]
    userId: int
    nickName: str
    grades: int
    landGrades: int
    gp: int
    totalGp: int
    todayFromFriendGp: int
    farmLandInfo: _containers.RepeatedCompositeFieldContainer[FarmLandInfoMsg]
    treeInfo: TreeInfoMsg
    todayStolenCount: int
    petInfo: _containers.RepeatedCompositeFieldContainer[FarmPetInfoMsg]
    guardPetInfo: FarmPetInfoMsg
    marriageTree: MarriageTreeMsg
    def __init__(self, userId: _Optional[int] = ..., nickName: _Optional[str] = ..., grades: _Optional[int] = ..., landGrades: _Optional[int] = ..., gp: _Optional[int] = ..., totalGp: _Optional[int] = ..., todayFromFriendGp: _Optional[int] = ..., farmLandInfo: _Optional[_Iterable[_Union[FarmLandInfoMsg, _Mapping]]] = ..., treeInfo: _Optional[_Union[TreeInfoMsg, _Mapping]] = ..., todayStolenCount: _Optional[int] = ..., petInfo: _Optional[_Iterable[_Union[FarmPetInfoMsg, _Mapping]]] = ..., guardPetInfo: _Optional[_Union[FarmPetInfoMsg, _Mapping]] = ..., marriageTree: _Optional[_Union[MarriageTreeMsg, _Mapping]] = ...) -> None: ...

class FarmLandInfoMsg(_message.Message):
    __slots__ = ("userId", "type", "pos", "itemTemplateId", "plantingTime", "matureTime", "cropState", "accelerateCount", "stolenCount", "isWormParam1", "isWormParam2", "isGrassParam1", "isGrassParam2", "stolenUsers", "rewardCount", "opType", "result", "param1", "param2")
    USERID_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    POS_FIELD_NUMBER: _ClassVar[int]
    ITEMTEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    PLANTINGTIME_FIELD_NUMBER: _ClassVar[int]
    MATURETIME_FIELD_NUMBER: _ClassVar[int]
    CROPSTATE_FIELD_NUMBER: _ClassVar[int]
    ACCELERATECOUNT_FIELD_NUMBER: _ClassVar[int]
    STOLENCOUNT_FIELD_NUMBER: _ClassVar[int]
    ISWORMPARAM1_FIELD_NUMBER: _ClassVar[int]
    ISWORMPARAM2_FIELD_NUMBER: _ClassVar[int]
    ISGRASSPARAM1_FIELD_NUMBER: _ClassVar[int]
    ISGRASSPARAM2_FIELD_NUMBER: _ClassVar[int]
    STOLENUSERS_FIELD_NUMBER: _ClassVar[int]
    REWARDCOUNT_FIELD_NUMBER: _ClassVar[int]
    OPTYPE_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    PARAM1_FIELD_NUMBER: _ClassVar[int]
    PARAM2_FIELD_NUMBER: _ClassVar[int]
    userId: int
    type: int
    pos: int
    itemTemplateId: int
    plantingTime: str
    matureTime: str
    cropState: int
    accelerateCount: int
    stolenCount: int
    isWormParam1: bool
    isWormParam2: bool
    isGrassParam1: bool
    isGrassParam2: bool
    stolenUsers: _containers.RepeatedScalarFieldContainer[int]
    rewardCount: int
    opType: int
    result: int
    param1: str
    param2: str
    def __init__(self, userId: _Optional[int] = ..., type: _Optional[int] = ..., pos: _Optional[int] = ..., itemTemplateId: _Optional[int] = ..., plantingTime: _Optional[str] = ..., matureTime: _Optional[str] = ..., cropState: _Optional[int] = ..., accelerateCount: _Optional[int] = ..., stolenCount: _Optional[int] = ..., isWormParam1: _Optional[bool] = ..., isWormParam2: _Optional[bool] = ..., isGrassParam1: _Optional[bool] = ..., isGrassParam2: _Optional[bool] = ..., stolenUsers: _Optional[_Iterable[int]] = ..., rewardCount: _Optional[int] = ..., opType: _Optional[int] = ..., result: _Optional[int] = ..., param1: _Optional[str] = ..., param2: _Optional[str] = ...) -> None: ...

class FarmLogReq(_message.Message):
    __slots__ = ("playerId", "operUserId", "operNickName", "desc", "operDate", "operCount", "isAddFavGp")
    PLAYERID_FIELD_NUMBER: _ClassVar[int]
    OPERUSERID_FIELD_NUMBER: _ClassVar[int]
    OPERNICKNAME_FIELD_NUMBER: _ClassVar[int]
    DESC_FIELD_NUMBER: _ClassVar[int]
    OPERDATE_FIELD_NUMBER: _ClassVar[int]
    OPERCOUNT_FIELD_NUMBER: _ClassVar[int]
    ISADDFAVGP_FIELD_NUMBER: _ClassVar[int]
    playerId: int
    operUserId: int
    operNickName: str
    desc: str
    operDate: bytes
    operCount: int
    isAddFavGp: bool
    def __init__(self, playerId: _Optional[int] = ..., operUserId: _Optional[int] = ..., operNickName: _Optional[str] = ..., desc: _Optional[str] = ..., operDate: _Optional[bytes] = ..., operCount: _Optional[int] = ..., isAddFavGp: _Optional[bool] = ...) -> None: ...

class FarmLogRsp(_message.Message):
    __slots__ = ("playerId", "operUserId", "operNickName", "desc", "operDate", "operCount", "isAddFavGp", "type")
    PLAYERID_FIELD_NUMBER: _ClassVar[int]
    OPERUSERID_FIELD_NUMBER: _ClassVar[int]
    OPERNICKNAME_FIELD_NUMBER: _ClassVar[int]
    DESC_FIELD_NUMBER: _ClassVar[int]
    OPERDATE_FIELD_NUMBER: _ClassVar[int]
    OPERCOUNT_FIELD_NUMBER: _ClassVar[int]
    ISADDFAVGP_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    playerId: int
    operUserId: int
    operNickName: str
    desc: str
    operDate: str
    operCount: int
    isAddFavGp: bool
    type: int
    def __init__(self, playerId: _Optional[int] = ..., operUserId: _Optional[int] = ..., operNickName: _Optional[str] = ..., desc: _Optional[str] = ..., operDate: _Optional[str] = ..., operCount: _Optional[int] = ..., isAddFavGp: _Optional[bool] = ..., type: _Optional[int] = ...) -> None: ...

class FarmOperReqMsg(_message.Message):
    __slots__ = ("userId", "friendId", "opType", "pos", "templateId", "payType", "bagPos")
    USERID_FIELD_NUMBER: _ClassVar[int]
    FRIENDID_FIELD_NUMBER: _ClassVar[int]
    OPTYPE_FIELD_NUMBER: _ClassVar[int]
    POS_FIELD_NUMBER: _ClassVar[int]
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    PAYTYPE_FIELD_NUMBER: _ClassVar[int]
    BAGPOS_FIELD_NUMBER: _ClassVar[int]
    userId: int
    friendId: int
    opType: int
    pos: int
    templateId: int
    payType: int
    bagPos: int
    def __init__(self, userId: _Optional[int] = ..., friendId: _Optional[int] = ..., opType: _Optional[int] = ..., pos: _Optional[int] = ..., templateId: _Optional[int] = ..., payType: _Optional[int] = ..., bagPos: _Optional[int] = ...) -> None: ...

class FarmPetInfoMsg(_message.Message):
    __slots__ = ("userId", "petId", "pos", "beginTime", "endTime", "petTemplateId", "state", "petName", "quality")
    USERID_FIELD_NUMBER: _ClassVar[int]
    PETID_FIELD_NUMBER: _ClassVar[int]
    POS_FIELD_NUMBER: _ClassVar[int]
    BEGINTIME_FIELD_NUMBER: _ClassVar[int]
    ENDTIME_FIELD_NUMBER: _ClassVar[int]
    PETTEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    PETNAME_FIELD_NUMBER: _ClassVar[int]
    QUALITY_FIELD_NUMBER: _ClassVar[int]
    userId: int
    petId: int
    pos: int
    beginTime: str
    endTime: str
    petTemplateId: int
    state: int
    petName: str
    quality: int
    def __init__(self, userId: _Optional[int] = ..., petId: _Optional[int] = ..., pos: _Optional[int] = ..., beginTime: _Optional[str] = ..., endTime: _Optional[str] = ..., petTemplateId: _Optional[int] = ..., state: _Optional[int] = ..., petName: _Optional[str] = ..., quality: _Optional[int] = ...) -> None: ...

class FarmRepMsg(_message.Message):
    __slots__ = ("farmLandInfo", "petInfo")
    FARMLANDINFO_FIELD_NUMBER: _ClassVar[int]
    PETINFO_FIELD_NUMBER: _ClassVar[int]
    farmLandInfo: FarmLandInfoMsg
    petInfo: _containers.RepeatedCompositeFieldContainer[FarmPetInfoMsg]
    def __init__(self, farmLandInfo: _Optional[_Union[FarmLandInfoMsg, _Mapping]] = ..., petInfo: _Optional[_Iterable[_Union[FarmPetInfoMsg, _Mapping]]] = ...) -> None: ...

class FashionBook(_message.Message):
    __slots__ = ("tempId", "isSwitch", "appraisalSkill")
    TEMPID_FIELD_NUMBER: _ClassVar[int]
    ISSWITCH_FIELD_NUMBER: _ClassVar[int]
    APPRAISALSKILL_FIELD_NUMBER: _ClassVar[int]
    tempId: int
    isSwitch: bool
    appraisalSkill: int
    def __init__(self, tempId: _Optional[int] = ..., isSwitch: _Optional[bool] = ..., appraisalSkill: _Optional[int] = ...) -> None: ...

class FashionInfoMsg(_message.Message):
    __slots__ = ("gp", "grades", "wingAvata", "hatAvata", "armAvata", "clothAvata", "isHidenWingAvata", "isHidenHatAvat", "isHidenArmAvata", "isHidenClothAvata", "dragonWingAvata", "dragonHatAvata", "dragonArmAvata", "dragonClothAvata", "isHidendDragonWingAvata", "isHidenDragonHatAvat", "isHidenDragonArmAvata", "isHidenDragonClothAvata", "defaultFashion")
    GP_FIELD_NUMBER: _ClassVar[int]
    GRADES_FIELD_NUMBER: _ClassVar[int]
    WINGAVATA_FIELD_NUMBER: _ClassVar[int]
    HATAVATA_FIELD_NUMBER: _ClassVar[int]
    ARMAVATA_FIELD_NUMBER: _ClassVar[int]
    CLOTHAVATA_FIELD_NUMBER: _ClassVar[int]
    ISHIDENWINGAVATA_FIELD_NUMBER: _ClassVar[int]
    ISHIDENHATAVAT_FIELD_NUMBER: _ClassVar[int]
    ISHIDENARMAVATA_FIELD_NUMBER: _ClassVar[int]
    ISHIDENCLOTHAVATA_FIELD_NUMBER: _ClassVar[int]
    DRAGONWINGAVATA_FIELD_NUMBER: _ClassVar[int]
    DRAGONHATAVATA_FIELD_NUMBER: _ClassVar[int]
    DRAGONARMAVATA_FIELD_NUMBER: _ClassVar[int]
    DRAGONCLOTHAVATA_FIELD_NUMBER: _ClassVar[int]
    ISHIDENDDRAGONWINGAVATA_FIELD_NUMBER: _ClassVar[int]
    ISHIDENDRAGONHATAVAT_FIELD_NUMBER: _ClassVar[int]
    ISHIDENDRAGONARMAVATA_FIELD_NUMBER: _ClassVar[int]
    ISHIDENDRAGONCLOTHAVATA_FIELD_NUMBER: _ClassVar[int]
    DEFAULTFASHION_FIELD_NUMBER: _ClassVar[int]
    gp: int
    grades: int
    wingAvata: int
    hatAvata: int
    armAvata: int
    clothAvata: int
    isHidenWingAvata: bool
    isHidenHatAvat: bool
    isHidenArmAvata: bool
    isHidenClothAvata: bool
    dragonWingAvata: int
    dragonHatAvata: int
    dragonArmAvata: int
    dragonClothAvata: int
    isHidendDragonWingAvata: bool
    isHidenDragonHatAvat: bool
    isHidenDragonArmAvata: bool
    isHidenDragonClothAvata: bool
    defaultFashion: int
    def __init__(self, gp: _Optional[int] = ..., grades: _Optional[int] = ..., wingAvata: _Optional[int] = ..., hatAvata: _Optional[int] = ..., armAvata: _Optional[int] = ..., clothAvata: _Optional[int] = ..., isHidenWingAvata: _Optional[bool] = ..., isHidenHatAvat: _Optional[bool] = ..., isHidenArmAvata: _Optional[bool] = ..., isHidenClothAvata: _Optional[bool] = ..., dragonWingAvata: _Optional[int] = ..., dragonHatAvata: _Optional[int] = ..., dragonArmAvata: _Optional[int] = ..., dragonClothAvata: _Optional[int] = ..., isHidendDragonWingAvata: _Optional[bool] = ..., isHidenDragonHatAvat: _Optional[bool] = ..., isHidenDragonArmAvata: _Optional[bool] = ..., isHidenDragonClothAvata: _Optional[bool] = ..., defaultFashion: _Optional[int] = ...) -> None: ...

class FashionMsg(_message.Message):
    __slots__ = ("templateId", "info", "fashionIds")
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    INFO_FIELD_NUMBER: _ClassVar[int]
    FASHIONIDS_FIELD_NUMBER: _ClassVar[int]
    templateId: int
    info: _containers.RepeatedCompositeFieldContainer[FashionBook]
    fashionIds: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, templateId: _Optional[int] = ..., info: _Optional[_Iterable[_Union[FashionBook, _Mapping]]] = ..., fashionIds: _Optional[_Iterable[int]] = ...) -> None: ...

class FashionPolishMsg(_message.Message):
    __slots__ = ("polishs",)
    POLISHS_FIELD_NUMBER: _ClassVar[int]
    polishs: _containers.RepeatedCompositeFieldContainer[PolishInfoMsg]
    def __init__(self, polishs: _Optional[_Iterable[_Union[PolishInfoMsg, _Mapping]]] = ...) -> None: ...

class FashionPolishRequestMsg(_message.Message):
    __slots__ = ("op", "sontype", "count")
    OP_FIELD_NUMBER: _ClassVar[int]
    SONTYPE_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    op: int
    sontype: int
    count: int
    def __init__(self, op: _Optional[int] = ..., sontype: _Optional[int] = ..., count: _Optional[int] = ...) -> None: ...

class FashionShopMsg(_message.Message):
    __slots__ = ("buyInfos", "result", "payType")
    BUYINFOS_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    PAYTYPE_FIELD_NUMBER: _ClassVar[int]
    buyInfos: _containers.RepeatedCompositeFieldContainer[BuyInfo]
    result: bool
    payType: int
    def __init__(self, buyInfos: _Optional[_Iterable[_Union[BuyInfo, _Mapping]]] = ..., result: _Optional[bool] = ..., payType: _Optional[int] = ...) -> None: ...

class FastOpenCustomerMsg(_message.Message):
    __slots__ = ("canOpen",)
    CANOPEN_FIELD_NUMBER: _ClassVar[int]
    canOpen: int
    def __init__(self, canOpen: _Optional[int] = ...) -> None: ...

class FastUseBloodMsg(_message.Message):
    __slots__ = ("result", "templateId")
    RESULT_FIELD_NUMBER: _ClassVar[int]
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    result: int
    templateId: int
    def __init__(self, result: _Optional[int] = ..., templateId: _Optional[int] = ...) -> None: ...

class FateEditMsg(_message.Message):
    __slots__ = ("skillSonType", "useItemCount", "isDisable", "turnNum", "param1", "param2", "isSuccess", "currCount", "count", "payType")
    SKILLSONTYPE_FIELD_NUMBER: _ClassVar[int]
    USEITEMCOUNT_FIELD_NUMBER: _ClassVar[int]
    ISDISABLE_FIELD_NUMBER: _ClassVar[int]
    TURNNUM_FIELD_NUMBER: _ClassVar[int]
    PARAM1_FIELD_NUMBER: _ClassVar[int]
    PARAM2_FIELD_NUMBER: _ClassVar[int]
    ISSUCCESS_FIELD_NUMBER: _ClassVar[int]
    CURRCOUNT_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    PAYTYPE_FIELD_NUMBER: _ClassVar[int]
    skillSonType: int
    useItemCount: int
    isDisable: bool
    turnNum: int
    param1: str
    param2: str
    isSuccess: bool
    currCount: int
    count: _containers.RepeatedScalarFieldContainer[int]
    payType: int
    def __init__(self, skillSonType: _Optional[int] = ..., useItemCount: _Optional[int] = ..., isDisable: _Optional[bool] = ..., turnNum: _Optional[int] = ..., param1: _Optional[str] = ..., param2: _Optional[str] = ..., isSuccess: _Optional[bool] = ..., currCount: _Optional[int] = ..., count: _Optional[_Iterable[int]] = ..., payType: _Optional[int] = ...) -> None: ...

class FateInfoMsg(_message.Message):
    __slots__ = ("templateId", "fateTypes", "totalGp", "grades", "property1", "property2", "turnCount")
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    FATETYPES_FIELD_NUMBER: _ClassVar[int]
    TOTALGP_FIELD_NUMBER: _ClassVar[int]
    GRADES_FIELD_NUMBER: _ClassVar[int]
    PROPERTY1_FIELD_NUMBER: _ClassVar[int]
    PROPERTY2_FIELD_NUMBER: _ClassVar[int]
    TURNCOUNT_FIELD_NUMBER: _ClassVar[int]
    templateId: int
    fateTypes: int
    totalGp: int
    grades: int
    property1: str
    property2: str
    turnCount: int
    def __init__(self, templateId: _Optional[int] = ..., fateTypes: _Optional[int] = ..., totalGp: _Optional[int] = ..., grades: _Optional[int] = ..., property1: _Optional[str] = ..., property2: _Optional[str] = ..., turnCount: _Optional[int] = ...) -> None: ...

class FateListMsg(_message.Message):
    __slots__ = ("fateInfo",)
    FATEINFO_FIELD_NUMBER: _ClassVar[int]
    fateInfo: _containers.RepeatedCompositeFieldContainer[FateInfoMsg]
    def __init__(self, fateInfo: _Optional[_Iterable[_Union[FateInfoMsg, _Mapping]]] = ...) -> None: ...

class FbEventMsg(_message.Message):
    __slots__ = ("id", "target")
    ID_FIELD_NUMBER: _ClassVar[int]
    TARGET_FIELD_NUMBER: _ClassVar[int]
    id: int
    target: str
    def __init__(self, id: _Optional[int] = ..., target: _Optional[str] = ...) -> None: ...

class FbShareMsg(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: int
    def __init__(self, id: _Optional[int] = ...) -> None: ...

class FightOverMoiveMsg(_message.Message):
    __slots__ = ("gp", "gold", "strategy")
    GP_FIELD_NUMBER: _ClassVar[int]
    GOLD_FIELD_NUMBER: _ClassVar[int]
    STRATEGY_FIELD_NUMBER: _ClassVar[int]
    gp: int
    gold: int
    strategy: int
    def __init__(self, gp: _Optional[int] = ..., gold: _Optional[int] = ..., strategy: _Optional[int] = ...) -> None: ...

class FightPlayerMsg(_message.Message):
    __slots__ = ("playerId", "nickName", "pic")
    PLAYERID_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    PIC_FIELD_NUMBER: _ClassVar[int]
    playerId: int
    nickName: str
    pic: int
    def __init__(self, playerId: _Optional[int] = ..., nickName: _Optional[str] = ..., pic: _Optional[int] = ...) -> None: ...

class FinishedReqMsg(_message.Message):
    __slots__ = ("templateId",)
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    templateId: int
    def __init__(self, templateId: _Optional[int] = ...) -> None: ...

class FishInfo(_message.Message):
    __slots__ = ("fishId", "templateId", "point", "beginTime", "channelId", "state", "now")
    FISHID_FIELD_NUMBER: _ClassVar[int]
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    POINT_FIELD_NUMBER: _ClassVar[int]
    BEGINTIME_FIELD_NUMBER: _ClassVar[int]
    CHANNELID_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    NOW_FIELD_NUMBER: _ClassVar[int]
    fishId: int
    templateId: int
    point: bool
    beginTime: int
    channelId: int
    state: int
    now: int
    def __init__(self, fishId: _Optional[int] = ..., templateId: _Optional[int] = ..., point: _Optional[bool] = ..., beginTime: _Optional[int] = ..., channelId: _Optional[int] = ..., state: _Optional[int] = ..., now: _Optional[int] = ...) -> None: ...

class FishInfosMsg(_message.Message):
    __slots__ = ("userId", "fishs")
    USERID_FIELD_NUMBER: _ClassVar[int]
    FISHS_FIELD_NUMBER: _ClassVar[int]
    userId: int
    fishs: _containers.RepeatedCompositeFieldContainer[FishInfo]
    def __init__(self, userId: _Optional[int] = ..., fishs: _Optional[_Iterable[_Union[FishInfo, _Mapping]]] = ...) -> None: ...

class FishPlayer(_message.Message):
    __slots__ = ("helpId", "nickName")
    HELPID_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    helpId: int
    nickName: str
    def __init__(self, helpId: _Optional[int] = ..., nickName: _Optional[str] = ...) -> None: ...

class FishPoolMsg(_message.Message):
    __slots__ = ("userId", "level", "gp", "score", "cd", "count", "maxCount", "tool1", "tool2", "tool3", "tool4", "hookState", "order", "fishplayers")
    USERID_FIELD_NUMBER: _ClassVar[int]
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    GP_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    CD_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    MAXCOUNT_FIELD_NUMBER: _ClassVar[int]
    TOOL1_FIELD_NUMBER: _ClassVar[int]
    TOOL2_FIELD_NUMBER: _ClassVar[int]
    TOOL3_FIELD_NUMBER: _ClassVar[int]
    TOOL4_FIELD_NUMBER: _ClassVar[int]
    HOOKSTATE_FIELD_NUMBER: _ClassVar[int]
    ORDER_FIELD_NUMBER: _ClassVar[int]
    FISHPLAYERS_FIELD_NUMBER: _ClassVar[int]
    userId: int
    level: int
    gp: int
    score: int
    cd: int
    count: int
    maxCount: int
    tool1: int
    tool2: int
    tool3: int
    tool4: int
    hookState: int
    order: int
    fishplayers: _containers.RepeatedCompositeFieldContainer[FishPlayer]
    def __init__(self, userId: _Optional[int] = ..., level: _Optional[int] = ..., gp: _Optional[int] = ..., score: _Optional[int] = ..., cd: _Optional[int] = ..., count: _Optional[int] = ..., maxCount: _Optional[int] = ..., tool1: _Optional[int] = ..., tool2: _Optional[int] = ..., tool3: _Optional[int] = ..., tool4: _Optional[int] = ..., hookState: _Optional[int] = ..., order: _Optional[int] = ..., fishplayers: _Optional[_Iterable[_Union[FishPlayer, _Mapping]]] = ...) -> None: ...

class FishResultMsg(_message.Message):
    __slots__ = ("userId", "results")
    USERID_FIELD_NUMBER: _ClassVar[int]
    RESULTS_FIELD_NUMBER: _ClassVar[int]
    userId: int
    results: _containers.RepeatedCompositeFieldContainer[Result]
    def __init__(self, userId: _Optional[int] = ..., results: _Optional[_Iterable[_Union[Result, _Mapping]]] = ...) -> None: ...

class FixAuctionItemRspMsg(_message.Message):
    __slots__ = ("result", "mallItemId")
    RESULT_FIELD_NUMBER: _ClassVar[int]
    MALLITEMID_FIELD_NUMBER: _ClassVar[int]
    result: int
    mallItemId: int
    def __init__(self, result: _Optional[int] = ..., mallItemId: _Optional[int] = ...) -> None: ...

class FogUpdateMsg(_message.Message):
    __slots__ = ("index", "fogByte")
    INDEX_FIELD_NUMBER: _ClassVar[int]
    FOGBYTE_FIELD_NUMBER: _ClassVar[int]
    index: int
    fogByte: int
    def __init__(self, index: _Optional[int] = ..., fogByte: _Optional[int] = ...) -> None: ...

class FreshPoolMsg(_message.Message):
    __slots__ = ("op", "paras")
    OP_FIELD_NUMBER: _ClassVar[int]
    PARAS_FIELD_NUMBER: _ClassVar[int]
    op: int
    paras: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, op: _Optional[int] = ..., paras: _Optional[_Iterable[int]] = ...) -> None: ...

class FriendAddedMsg(_message.Message):
    __slots__ = ("userId", "nickName", "grades", "sex")
    USERID_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    GRADES_FIELD_NUMBER: _ClassVar[int]
    SEX_FIELD_NUMBER: _ClassVar[int]
    userId: int
    nickName: str
    grades: int
    sex: int
    def __init__(self, userId: _Optional[int] = ..., nickName: _Optional[str] = ..., grades: _Optional[int] = ..., sex: _Optional[int] = ...) -> None: ...

class FriendFarmStateMsg(_message.Message):
    __slots__ = ("userId", "isReap", "isChargeEnergy", "isRevive", "isWorm", "isGrass", "isFeed")
    USERID_FIELD_NUMBER: _ClassVar[int]
    ISREAP_FIELD_NUMBER: _ClassVar[int]
    ISCHARGEENERGY_FIELD_NUMBER: _ClassVar[int]
    ISREVIVE_FIELD_NUMBER: _ClassVar[int]
    ISWORM_FIELD_NUMBER: _ClassVar[int]
    ISGRASS_FIELD_NUMBER: _ClassVar[int]
    ISFEED_FIELD_NUMBER: _ClassVar[int]
    userId: int
    isReap: bool
    isChargeEnergy: bool
    isRevive: bool
    isWorm: bool
    isGrass: bool
    isFeed: bool
    def __init__(self, userId: _Optional[int] = ..., isReap: _Optional[bool] = ..., isChargeEnergy: _Optional[bool] = ..., isRevive: _Optional[bool] = ..., isWorm: _Optional[bool] = ..., isGrass: _Optional[bool] = ..., isFeed: _Optional[bool] = ...) -> None: ...

class FriendGroupMsg(_message.Message):
    __slots__ = ("groupId", "groupName", "result")
    GROUPID_FIELD_NUMBER: _ClassVar[int]
    GROUPNAME_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    groupId: int
    groupName: str
    result: int
    def __init__(self, groupId: _Optional[int] = ..., groupName: _Optional[str] = ..., result: _Optional[int] = ...) -> None: ...

class FriendInfoMsg(_message.Message):
    __slots__ = ("userId", "relation", "sex", "pic", "grades", "nickName", "onlineState", "relationGrade", "relationGp", "consortiaId", "consortiaName", "result", "addMsg", "fightCapacity", "job", "groupId", "expAdded", "snsInfo", "chatState", "vipType", "isVip")
    USERID_FIELD_NUMBER: _ClassVar[int]
    RELATION_FIELD_NUMBER: _ClassVar[int]
    SEX_FIELD_NUMBER: _ClassVar[int]
    PIC_FIELD_NUMBER: _ClassVar[int]
    GRADES_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    ONLINESTATE_FIELD_NUMBER: _ClassVar[int]
    RELATIONGRADE_FIELD_NUMBER: _ClassVar[int]
    RELATIONGP_FIELD_NUMBER: _ClassVar[int]
    CONSORTIAID_FIELD_NUMBER: _ClassVar[int]
    CONSORTIANAME_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    ADDMSG_FIELD_NUMBER: _ClassVar[int]
    FIGHTCAPACITY_FIELD_NUMBER: _ClassVar[int]
    JOB_FIELD_NUMBER: _ClassVar[int]
    GROUPID_FIELD_NUMBER: _ClassVar[int]
    EXPADDED_FIELD_NUMBER: _ClassVar[int]
    SNSINFO_FIELD_NUMBER: _ClassVar[int]
    CHATSTATE_FIELD_NUMBER: _ClassVar[int]
    VIPTYPE_FIELD_NUMBER: _ClassVar[int]
    ISVIP_FIELD_NUMBER: _ClassVar[int]
    userId: int
    relation: int
    sex: int
    pic: int
    grades: int
    nickName: str
    onlineState: int
    relationGrade: int
    relationGp: int
    consortiaId: int
    consortiaName: str
    result: bool
    addMsg: str
    fightCapacity: int
    job: int
    groupId: int
    expAdded: int
    snsInfo: SNSInfoMsg
    chatState: int
    vipType: int
    isVip: bool
    def __init__(self, userId: _Optional[int] = ..., relation: _Optional[int] = ..., sex: _Optional[int] = ..., pic: _Optional[int] = ..., grades: _Optional[int] = ..., nickName: _Optional[str] = ..., onlineState: _Optional[int] = ..., relationGrade: _Optional[int] = ..., relationGp: _Optional[int] = ..., consortiaId: _Optional[int] = ..., consortiaName: _Optional[str] = ..., result: _Optional[bool] = ..., addMsg: _Optional[str] = ..., fightCapacity: _Optional[int] = ..., job: _Optional[int] = ..., groupId: _Optional[int] = ..., expAdded: _Optional[int] = ..., snsInfo: _Optional[_Union[SNSInfoMsg, _Mapping]] = ..., chatState: _Optional[int] = ..., vipType: _Optional[int] = ..., isVip: _Optional[bool] = ...) -> None: ...

class FriendPlayer(_message.Message):
    __slots__ = ("playerId", "nickName", "level", "sex", "attack", "mapName", "transGrade", "job", "changeBranch")
    PLAYERID_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    SEX_FIELD_NUMBER: _ClassVar[int]
    ATTACK_FIELD_NUMBER: _ClassVar[int]
    MAPNAME_FIELD_NUMBER: _ClassVar[int]
    TRANSGRADE_FIELD_NUMBER: _ClassVar[int]
    JOB_FIELD_NUMBER: _ClassVar[int]
    CHANGEBRANCH_FIELD_NUMBER: _ClassVar[int]
    playerId: int
    nickName: str
    level: int
    sex: int
    attack: int
    mapName: str
    transGrade: int
    job: int
    changeBranch: int
    def __init__(self, playerId: _Optional[int] = ..., nickName: _Optional[str] = ..., level: _Optional[int] = ..., sex: _Optional[int] = ..., attack: _Optional[int] = ..., mapName: _Optional[str] = ..., transGrade: _Optional[int] = ..., job: _Optional[int] = ..., changeBranch: _Optional[int] = ...) -> None: ...

class FriendRelationList(_message.Message):
    __slots__ = ("relationList", "group", "maxPage", "curPage")
    RELATIONLIST_FIELD_NUMBER: _ClassVar[int]
    GROUP_FIELD_NUMBER: _ClassVar[int]
    MAXPAGE_FIELD_NUMBER: _ClassVar[int]
    CURPAGE_FIELD_NUMBER: _ClassVar[int]
    relationList: _containers.RepeatedCompositeFieldContainer[RelationPlayerMsg]
    group: _containers.RepeatedCompositeFieldContainer[FriendGroupMsg]
    maxPage: int
    curPage: int
    def __init__(self, relationList: _Optional[_Iterable[_Union[RelationPlayerMsg, _Mapping]]] = ..., group: _Optional[_Iterable[_Union[FriendGroupMsg, _Mapping]]] = ..., maxPage: _Optional[int] = ..., curPage: _Optional[int] = ...) -> None: ...

class FriendRelationMsg(_message.Message):
    __slots__ = ("otherId", "nickName", "relation", "noticeMsg", "result")
    OTHERID_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    RELATION_FIELD_NUMBER: _ClassVar[int]
    NOTICEMSG_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    otherId: int
    nickName: str
    relation: int
    noticeMsg: str
    result: bool
    def __init__(self, otherId: _Optional[int] = ..., nickName: _Optional[str] = ..., relation: _Optional[int] = ..., noticeMsg: _Optional[str] = ..., result: _Optional[bool] = ...) -> None: ...

class FriendSearchConditionReqMsg(_message.Message):
    __slots__ = ("pageIndex", "sex", "birthMonth", "birthDay", "starId", "bloodType", "country", "province", "city")
    PAGEINDEX_FIELD_NUMBER: _ClassVar[int]
    SEX_FIELD_NUMBER: _ClassVar[int]
    BIRTHMONTH_FIELD_NUMBER: _ClassVar[int]
    BIRTHDAY_FIELD_NUMBER: _ClassVar[int]
    STARID_FIELD_NUMBER: _ClassVar[int]
    BLOODTYPE_FIELD_NUMBER: _ClassVar[int]
    COUNTRY_FIELD_NUMBER: _ClassVar[int]
    PROVINCE_FIELD_NUMBER: _ClassVar[int]
    CITY_FIELD_NUMBER: _ClassVar[int]
    pageIndex: int
    sex: int
    birthMonth: int
    birthDay: int
    starId: int
    bloodType: int
    country: int
    province: int
    city: int
    def __init__(self, pageIndex: _Optional[int] = ..., sex: _Optional[int] = ..., birthMonth: _Optional[int] = ..., birthDay: _Optional[int] = ..., starId: _Optional[int] = ..., bloodType: _Optional[int] = ..., country: _Optional[int] = ..., province: _Optional[int] = ..., city: _Optional[int] = ...) -> None: ...

class FriendSearchRspMsg(_message.Message):
    __slots__ = ("totalRows", "snsInfo")
    TOTALROWS_FIELD_NUMBER: _ClassVar[int]
    SNSINFO_FIELD_NUMBER: _ClassVar[int]
    totalRows: int
    snsInfo: _containers.RepeatedCompositeFieldContainer[SNSInfoMsg]
    def __init__(self, totalRows: _Optional[int] = ..., snsInfo: _Optional[_Iterable[_Union[SNSInfoMsg, _Mapping]]] = ...) -> None: ...

class FriendTreeReq(_message.Message):
    __slots__ = ("friendId",)
    FRIENDID_FIELD_NUMBER: _ClassVar[int]
    friendId: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, friendId: _Optional[_Iterable[int]] = ...) -> None: ...

class FriendTreeRsp(_message.Message):
    __slots__ = ("treeInfo",)
    TREEINFO_FIELD_NUMBER: _ClassVar[int]
    treeInfo: _containers.RepeatedCompositeFieldContainer[TreeInfoMsg]
    def __init__(self, treeInfo: _Optional[_Iterable[_Union[TreeInfoMsg, _Mapping]]] = ...) -> None: ...

class FriendUserIdsMsg(_message.Message):
    __slots__ = ("friendId",)
    FRIENDID_FIELD_NUMBER: _ClassVar[int]
    friendId: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, friendId: _Optional[_Iterable[int]] = ...) -> None: ...

class GItemInfoMsg(_message.Message):
    __slots__ = ("templateId", "count")
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    templateId: int
    count: int
    def __init__(self, templateId: _Optional[int] = ..., count: _Optional[int] = ...) -> None: ...

class GameStoryMsg(_message.Message):
    __slots__ = ("isAccess", "index", "isDrop")
    ISACCESS_FIELD_NUMBER: _ClassVar[int]
    INDEX_FIELD_NUMBER: _ClassVar[int]
    ISDROP_FIELD_NUMBER: _ClassVar[int]
    isAccess: bool
    index: int
    isDrop: bool
    def __init__(self, isAccess: _Optional[bool] = ..., index: _Optional[int] = ..., isDrop: _Optional[bool] = ...) -> None: ...

class GatewayMsg(_message.Message):
    __slots__ = ("notifyMsg",)
    NOTIFYMSG_FIELD_NUMBER: _ClassVar[int]
    notifyMsg: str
    def __init__(self, notifyMsg: _Optional[str] = ...) -> None: ...

class GemInfoMsg(_message.Message):
    __slots__ = ("mark", "color")
    MARK_FIELD_NUMBER: _ClassVar[int]
    COLOR_FIELD_NUMBER: _ClassVar[int]
    mark: int
    color: int
    def __init__(self, mark: _Optional[int] = ..., color: _Optional[int] = ...) -> None: ...

class GemInfoUpdateMsg(_message.Message):
    __slots__ = ("gemDel", "gemAdd", "score", "curExp", "maxExp", "gemLevel", "scoreOrder", "rewardInfo")
    GEMDEL_FIELD_NUMBER: _ClassVar[int]
    GEMADD_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    CUREXP_FIELD_NUMBER: _ClassVar[int]
    MAXEXP_FIELD_NUMBER: _ClassVar[int]
    GEMLEVEL_FIELD_NUMBER: _ClassVar[int]
    SCOREORDER_FIELD_NUMBER: _ClassVar[int]
    REWARDINFO_FIELD_NUMBER: _ClassVar[int]
    gemDel: _containers.RepeatedCompositeFieldContainer[GemInfoMsg]
    gemAdd: _containers.RepeatedCompositeFieldContainer[GemInfoMsg]
    score: _containers.RepeatedScalarFieldContainer[int]
    curExp: int
    maxExp: int
    gemLevel: int
    scoreOrder: int
    rewardInfo: _containers.RepeatedCompositeFieldContainer[RewardInfoMsg]
    def __init__(self, gemDel: _Optional[_Iterable[_Union[GemInfoMsg, _Mapping]]] = ..., gemAdd: _Optional[_Iterable[_Union[GemInfoMsg, _Mapping]]] = ..., score: _Optional[_Iterable[int]] = ..., curExp: _Optional[int] = ..., maxExp: _Optional[int] = ..., gemLevel: _Optional[int] = ..., scoreOrder: _Optional[int] = ..., rewardInfo: _Optional[_Iterable[_Union[RewardInfoMsg, _Mapping]]] = ...) -> None: ...

class GemInviteOpMsg(_message.Message):
    __slots__ = ("playerId", "opCode")
    PLAYERID_FIELD_NUMBER: _ClassVar[int]
    OPCODE_FIELD_NUMBER: _ClassVar[int]
    playerId: int
    opCode: int
    def __init__(self, playerId: _Optional[int] = ..., opCode: _Optional[int] = ...) -> None: ...

class GemMazeBuyTimesMsg(_message.Message):
    __slots__ = ("buyTypes",)
    BUYTYPES_FIELD_NUMBER: _ClassVar[int]
    buyTypes: int
    def __init__(self, buyTypes: _Optional[int] = ...) -> None: ...

class GemMazeBuyTimesRspMsg(_message.Message):
    __slots__ = ("moveTimesLeft",)
    MOVETIMESLEFT_FIELD_NUMBER: _ClassVar[int]
    moveTimesLeft: int
    def __init__(self, moveTimesLeft: _Optional[int] = ...) -> None: ...

class GemMazeInfoMsg(_message.Message):
    __slots__ = ("allGems", "score", "weekScore", "timesLeft", "buyTimesLeft", "helpTimesLeft", "gemLevel", "curExp", "maxExp", "boxMark", "scoreOrder", "boxesId")
    ALLGEMS_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    WEEKSCORE_FIELD_NUMBER: _ClassVar[int]
    TIMESLEFT_FIELD_NUMBER: _ClassVar[int]
    BUYTIMESLEFT_FIELD_NUMBER: _ClassVar[int]
    HELPTIMESLEFT_FIELD_NUMBER: _ClassVar[int]
    GEMLEVEL_FIELD_NUMBER: _ClassVar[int]
    CUREXP_FIELD_NUMBER: _ClassVar[int]
    MAXEXP_FIELD_NUMBER: _ClassVar[int]
    BOXMARK_FIELD_NUMBER: _ClassVar[int]
    SCOREORDER_FIELD_NUMBER: _ClassVar[int]
    BOXESID_FIELD_NUMBER: _ClassVar[int]
    allGems: _containers.RepeatedCompositeFieldContainer[GemInfoMsg]
    score: int
    weekScore: int
    timesLeft: int
    buyTimesLeft: int
    helpTimesLeft: int
    gemLevel: int
    curExp: int
    maxExp: int
    boxMark: int
    scoreOrder: int
    boxesId: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, allGems: _Optional[_Iterable[_Union[GemInfoMsg, _Mapping]]] = ..., score: _Optional[int] = ..., weekScore: _Optional[int] = ..., timesLeft: _Optional[int] = ..., buyTimesLeft: _Optional[int] = ..., helpTimesLeft: _Optional[int] = ..., gemLevel: _Optional[int] = ..., curExp: _Optional[int] = ..., maxExp: _Optional[int] = ..., boxMark: _Optional[int] = ..., scoreOrder: _Optional[int] = ..., boxesId: _Optional[_Iterable[int]] = ...) -> None: ...

class GemMazeOpRstMsg(_message.Message):
    __slots__ = ("rstCode",)
    RSTCODE_FIELD_NUMBER: _ClassVar[int]
    rstCode: int
    def __init__(self, rstCode: _Optional[int] = ...) -> None: ...

class GemMoveInviteMsg(_message.Message):
    __slots__ = ("playerIdInvited",)
    PLAYERIDINVITED_FIELD_NUMBER: _ClassVar[int]
    playerIdInvited: int
    def __init__(self, playerIdInvited: _Optional[int] = ...) -> None: ...

class GemMoveInviteReqMsg(_message.Message):
    __slots__ = ("friendId", "inviteTimes", "helpNums")
    FRIENDID_FIELD_NUMBER: _ClassVar[int]
    INVITETIMES_FIELD_NUMBER: _ClassVar[int]
    HELPNUMS_FIELD_NUMBER: _ClassVar[int]
    friendId: int
    inviteTimes: int
    helpNums: int
    def __init__(self, friendId: _Optional[int] = ..., inviteTimes: _Optional[int] = ..., helpNums: _Optional[int] = ...) -> None: ...

class GemMoveMsg(_message.Message):
    __slots__ = ("beginMark", "endMark")
    BEGINMARK_FIELD_NUMBER: _ClassVar[int]
    ENDMARK_FIELD_NUMBER: _ClassVar[int]
    beginMark: int
    endMark: int
    def __init__(self, beginMark: _Optional[int] = ..., endMark: _Optional[int] = ...) -> None: ...

class GetItemInfosMsg(_message.Message):
    __slots__ = ("interval", "times", "itemInfo")
    INTERVAL_FIELD_NUMBER: _ClassVar[int]
    TIMES_FIELD_NUMBER: _ClassVar[int]
    ITEMINFO_FIELD_NUMBER: _ClassVar[int]
    interval: int
    times: int
    itemInfo: _containers.RepeatedCompositeFieldContainer[GItemInfoMsg]
    def __init__(self, interval: _Optional[int] = ..., times: _Optional[int] = ..., itemInfo: _Optional[_Iterable[_Union[GItemInfoMsg, _Mapping]]] = ...) -> None: ...

class GetLogMsg(_message.Message):
    __slots__ = ("type", "time")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    TIME_FIELD_NUMBER: _ClassVar[int]
    type: int
    time: int
    def __init__(self, type: _Optional[int] = ..., time: _Optional[int] = ...) -> None: ...

class GetRewardBoxMsg(_message.Message):
    __slots__ = ("boxId",)
    BOXID_FIELD_NUMBER: _ClassVar[int]
    boxId: int
    def __init__(self, boxId: _Optional[int] = ...) -> None: ...

class GetRewardBoxRspMsg(_message.Message):
    __slots__ = ("boxGetMark", "rewardInfo")
    BOXGETMARK_FIELD_NUMBER: _ClassVar[int]
    REWARDINFO_FIELD_NUMBER: _ClassVar[int]
    boxGetMark: int
    rewardInfo: _containers.RepeatedCompositeFieldContainer[RewardInfoMsg]
    def __init__(self, boxGetMark: _Optional[int] = ..., rewardInfo: _Optional[_Iterable[_Union[RewardInfoMsg, _Mapping]]] = ...) -> None: ...

class GetRewardMsg(_message.Message):
    __slots__ = ("day",)
    DAY_FIELD_NUMBER: _ClassVar[int]
    day: int
    def __init__(self, day: _Optional[int] = ...) -> None: ...

class GiveupWildLandMsg(_message.Message):
    __slots__ = ("wildLandPos",)
    WILDLANDPOS_FIELD_NUMBER: _ClassVar[int]
    wildLandPos: str
    def __init__(self, wildLandPos: _Optional[str] = ...) -> None: ...

class GoldImposeMsg(_message.Message):
    __slots__ = ("leftImpose", "maxImpose")
    LEFTIMPOSE_FIELD_NUMBER: _ClassVar[int]
    MAXIMPOSE_FIELD_NUMBER: _ClassVar[int]
    leftImpose: int
    maxImpose: int
    def __init__(self, leftImpose: _Optional[int] = ..., maxImpose: _Optional[int] = ...) -> None: ...

class GoldenRoadClientRequestMsg(_message.Message):
    __slots__ = ("consumeType", "diceType", "refreshType", "requestBroadcast", "bagOPType", "isBatch")
    CONSUMETYPE_FIELD_NUMBER: _ClassVar[int]
    DICETYPE_FIELD_NUMBER: _ClassVar[int]
    REFRESHTYPE_FIELD_NUMBER: _ClassVar[int]
    REQUESTBROADCAST_FIELD_NUMBER: _ClassVar[int]
    BAGOPTYPE_FIELD_NUMBER: _ClassVar[int]
    ISBATCH_FIELD_NUMBER: _ClassVar[int]
    consumeType: int
    diceType: int
    refreshType: int
    requestBroadcast: bool
    bagOPType: int
    isBatch: bool
    def __init__(self, consumeType: _Optional[int] = ..., diceType: _Optional[int] = ..., refreshType: _Optional[int] = ..., requestBroadcast: _Optional[bool] = ..., bagOPType: _Optional[int] = ..., isBatch: _Optional[bool] = ...) -> None: ...

class GoldenRoadMsg(_message.Message):
    __slots__ = ("playerStatue", "score", "cellInfo")
    PLAYERSTATUE_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    CELLINFO_FIELD_NUMBER: _ClassVar[int]
    playerStatue: int
    score: int
    cellInfo: _containers.RepeatedCompositeFieldContainer[CellInfoMsg]
    def __init__(self, playerStatue: _Optional[int] = ..., score: _Optional[int] = ..., cellInfo: _Optional[_Iterable[_Union[CellInfoMsg, _Mapping]]] = ...) -> None: ...

class GrouponShopMsg(_message.Message):
    __slots__ = ("buyCount", "totalPoint", "curPrice", "curCount", "goodId", "param1", "param2", "count", "isReward", "frontMoney")
    BUYCOUNT_FIELD_NUMBER: _ClassVar[int]
    TOTALPOINT_FIELD_NUMBER: _ClassVar[int]
    CURPRICE_FIELD_NUMBER: _ClassVar[int]
    CURCOUNT_FIELD_NUMBER: _ClassVar[int]
    GOODID_FIELD_NUMBER: _ClassVar[int]
    PARAM1_FIELD_NUMBER: _ClassVar[int]
    PARAM2_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    ISREWARD_FIELD_NUMBER: _ClassVar[int]
    FRONTMONEY_FIELD_NUMBER: _ClassVar[int]
    buyCount: int
    totalPoint: int
    curPrice: int
    curCount: int
    goodId: int
    param1: int
    param2: str
    count: int
    isReward: bool
    frontMoney: int
    def __init__(self, buyCount: _Optional[int] = ..., totalPoint: _Optional[int] = ..., curPrice: _Optional[int] = ..., curCount: _Optional[int] = ..., goodId: _Optional[int] = ..., param1: _Optional[int] = ..., param2: _Optional[str] = ..., count: _Optional[int] = ..., isReward: _Optional[bool] = ..., frontMoney: _Optional[int] = ...) -> None: ...

class GuildBufferListMsg(_message.Message):
    __slots__ = ("consortiaId", "buffers")
    CONSORTIAID_FIELD_NUMBER: _ClassVar[int]
    BUFFERS_FIELD_NUMBER: _ClassVar[int]
    consortiaId: int
    buffers: _containers.RepeatedCompositeFieldContainer[GuildBufferMsg]
    def __init__(self, consortiaId: _Optional[int] = ..., buffers: _Optional[_Iterable[_Union[GuildBufferMsg, _Mapping]]] = ...) -> None: ...

class GuildBufferMsg(_message.Message):
    __slots__ = ("templateId", "consortiaId", "bufferName", "curreCount", "maxCdTimer", "objectData", "needPay", "descr", "param1", "maxBuyCount")
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    CONSORTIAID_FIELD_NUMBER: _ClassVar[int]
    BUFFERNAME_FIELD_NUMBER: _ClassVar[int]
    CURRECOUNT_FIELD_NUMBER: _ClassVar[int]
    MAXCDTIMER_FIELD_NUMBER: _ClassVar[int]
    OBJECTDATA_FIELD_NUMBER: _ClassVar[int]
    NEEDPAY_FIELD_NUMBER: _ClassVar[int]
    DESCR_FIELD_NUMBER: _ClassVar[int]
    PARAM1_FIELD_NUMBER: _ClassVar[int]
    MAXBUYCOUNT_FIELD_NUMBER: _ClassVar[int]
    templateId: int
    consortiaId: int
    bufferName: str
    curreCount: int
    maxCdTimer: int
    objectData: int
    needPay: int
    descr: str
    param1: str
    maxBuyCount: int
    def __init__(self, templateId: _Optional[int] = ..., consortiaId: _Optional[int] = ..., bufferName: _Optional[str] = ..., curreCount: _Optional[int] = ..., maxCdTimer: _Optional[int] = ..., objectData: _Optional[int] = ..., needPay: _Optional[int] = ..., descr: _Optional[str] = ..., param1: _Optional[str] = ..., maxBuyCount: _Optional[int] = ...) -> None: ...

class GuildChallengeInfoMsg(_message.Message):
    __slots__ = ("isExist", "startTime", "endTime", "attackGuildId", "defencGuildId", "attackName", "defencName")
    ISEXIST_FIELD_NUMBER: _ClassVar[int]
    STARTTIME_FIELD_NUMBER: _ClassVar[int]
    ENDTIME_FIELD_NUMBER: _ClassVar[int]
    ATTACKGUILDID_FIELD_NUMBER: _ClassVar[int]
    DEFENCGUILDID_FIELD_NUMBER: _ClassVar[int]
    ATTACKNAME_FIELD_NUMBER: _ClassVar[int]
    DEFENCNAME_FIELD_NUMBER: _ClassVar[int]
    isExist: bool
    startTime: str
    endTime: str
    attackGuildId: int
    defencGuildId: int
    attackName: str
    defencName: str
    def __init__(self, isExist: _Optional[bool] = ..., startTime: _Optional[str] = ..., endTime: _Optional[str] = ..., attackGuildId: _Optional[int] = ..., defencGuildId: _Optional[int] = ..., attackName: _Optional[str] = ..., defencName: _Optional[str] = ...) -> None: ...

class GuildChallengeOrderListMsg(_message.Message):
    __slots__ = ("info", "guildName", "guildGrade", "guildOffer", "guildOrder", "guildFighPower", "challenge")
    INFO_FIELD_NUMBER: _ClassVar[int]
    GUILDNAME_FIELD_NUMBER: _ClassVar[int]
    GUILDGRADE_FIELD_NUMBER: _ClassVar[int]
    GUILDOFFER_FIELD_NUMBER: _ClassVar[int]
    GUILDORDER_FIELD_NUMBER: _ClassVar[int]
    GUILDFIGHPOWER_FIELD_NUMBER: _ClassVar[int]
    CHALLENGE_FIELD_NUMBER: _ClassVar[int]
    info: _containers.RepeatedCompositeFieldContainer[GuildOrderInfoMsg]
    guildName: str
    guildGrade: int
    guildOffer: int
    guildOrder: int
    guildFighPower: int
    challenge: _containers.RepeatedCompositeFieldContainer[GuildChallengeInfoMsg]
    def __init__(self, info: _Optional[_Iterable[_Union[GuildOrderInfoMsg, _Mapping]]] = ..., guildName: _Optional[str] = ..., guildGrade: _Optional[int] = ..., guildOffer: _Optional[int] = ..., guildOrder: _Optional[int] = ..., guildFighPower: _Optional[int] = ..., challenge: _Optional[_Iterable[_Union[GuildChallengeInfoMsg, _Mapping]]] = ...) -> None: ...

class GuildGroupListMsg(_message.Message):
    __slots__ = ("group", "orderTime", "isGuildSize")
    GROUP_FIELD_NUMBER: _ClassVar[int]
    ORDERTIME_FIELD_NUMBER: _ClassVar[int]
    ISGUILDSIZE_FIELD_NUMBER: _ClassVar[int]
    group: _containers.RepeatedCompositeFieldContainer[GuildGroupMsg]
    orderTime: str
    isGuildSize: bool
    def __init__(self, group: _Optional[_Iterable[_Union[GuildGroupMsg, _Mapping]]] = ..., orderTime: _Optional[str] = ..., isGuildSize: _Optional[bool] = ...) -> None: ...

class GuildGroupMsg(_message.Message):
    __slots__ = ("consortiaId", "consortiaName", "group1", "group2", "group3", "group4", "result1", "result2", "result3", "result4", "score", "order", "fightPower")
    CONSORTIAID_FIELD_NUMBER: _ClassVar[int]
    CONSORTIANAME_FIELD_NUMBER: _ClassVar[int]
    GROUP1_FIELD_NUMBER: _ClassVar[int]
    GROUP2_FIELD_NUMBER: _ClassVar[int]
    GROUP3_FIELD_NUMBER: _ClassVar[int]
    GROUP4_FIELD_NUMBER: _ClassVar[int]
    RESULT1_FIELD_NUMBER: _ClassVar[int]
    RESULT2_FIELD_NUMBER: _ClassVar[int]
    RESULT3_FIELD_NUMBER: _ClassVar[int]
    RESULT4_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    ORDER_FIELD_NUMBER: _ClassVar[int]
    FIGHTPOWER_FIELD_NUMBER: _ClassVar[int]
    consortiaId: int
    consortiaName: str
    group1: int
    group2: int
    group3: int
    group4: int
    result1: int
    result2: int
    result3: int
    result4: int
    score: int
    order: int
    fightPower: int
    def __init__(self, consortiaId: _Optional[int] = ..., consortiaName: _Optional[str] = ..., group1: _Optional[int] = ..., group2: _Optional[int] = ..., group3: _Optional[int] = ..., group4: _Optional[int] = ..., result1: _Optional[int] = ..., result2: _Optional[int] = ..., result3: _Optional[int] = ..., result4: _Optional[int] = ..., score: _Optional[int] = ..., order: _Optional[int] = ..., fightPower: _Optional[int] = ...) -> None: ...

class GuildInfoMsg(_message.Message):
    __slots__ = ("uid", "guildId", "consortiaName", "totalScore", "fightPower", "site", "crossServerId", "warIndex", "groupId", "crossOrder", "playerCount", "winCount", "result1", "result2", "result3", "states", "finalTeam", "serverName", "heroInfo")
    UID_FIELD_NUMBER: _ClassVar[int]
    GUILDID_FIELD_NUMBER: _ClassVar[int]
    CONSORTIANAME_FIELD_NUMBER: _ClassVar[int]
    TOTALSCORE_FIELD_NUMBER: _ClassVar[int]
    FIGHTPOWER_FIELD_NUMBER: _ClassVar[int]
    SITE_FIELD_NUMBER: _ClassVar[int]
    CROSSSERVERID_FIELD_NUMBER: _ClassVar[int]
    WARINDEX_FIELD_NUMBER: _ClassVar[int]
    GROUPID_FIELD_NUMBER: _ClassVar[int]
    CROSSORDER_FIELD_NUMBER: _ClassVar[int]
    PLAYERCOUNT_FIELD_NUMBER: _ClassVar[int]
    WINCOUNT_FIELD_NUMBER: _ClassVar[int]
    RESULT1_FIELD_NUMBER: _ClassVar[int]
    RESULT2_FIELD_NUMBER: _ClassVar[int]
    RESULT3_FIELD_NUMBER: _ClassVar[int]
    STATES_FIELD_NUMBER: _ClassVar[int]
    FINALTEAM_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    HEROINFO_FIELD_NUMBER: _ClassVar[int]
    uid: str
    guildId: int
    consortiaName: str
    totalScore: int
    fightPower: int
    site: str
    crossServerId: int
    warIndex: int
    groupId: int
    crossOrder: int
    playerCount: int
    winCount: int
    result1: int
    result2: int
    result3: int
    states: int
    finalTeam: int
    serverName: str
    heroInfo: str
    def __init__(self, uid: _Optional[str] = ..., guildId: _Optional[int] = ..., consortiaName: _Optional[str] = ..., totalScore: _Optional[int] = ..., fightPower: _Optional[int] = ..., site: _Optional[str] = ..., crossServerId: _Optional[int] = ..., warIndex: _Optional[int] = ..., groupId: _Optional[int] = ..., crossOrder: _Optional[int] = ..., playerCount: _Optional[int] = ..., winCount: _Optional[int] = ..., result1: _Optional[int] = ..., result2: _Optional[int] = ..., result3: _Optional[int] = ..., states: _Optional[int] = ..., finalTeam: _Optional[int] = ..., serverName: _Optional[str] = ..., heroInfo: _Optional[str] = ...) -> None: ...

class GuildJoinPlayerInfoMsg(_message.Message):
    __slots__ = ("redConsortiaId", "redCount", "redLevel", "blueConsortiaId", "blueCount", "blueLevel", "userIds", "state")
    REDCONSORTIAID_FIELD_NUMBER: _ClassVar[int]
    REDCOUNT_FIELD_NUMBER: _ClassVar[int]
    REDLEVEL_FIELD_NUMBER: _ClassVar[int]
    BLUECONSORTIAID_FIELD_NUMBER: _ClassVar[int]
    BLUECOUNT_FIELD_NUMBER: _ClassVar[int]
    BLUELEVEL_FIELD_NUMBER: _ClassVar[int]
    USERIDS_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    redConsortiaId: int
    redCount: int
    redLevel: int
    blueConsortiaId: int
    blueCount: int
    blueLevel: int
    userIds: _containers.RepeatedScalarFieldContainer[int]
    state: int
    def __init__(self, redConsortiaId: _Optional[int] = ..., redCount: _Optional[int] = ..., redLevel: _Optional[int] = ..., blueConsortiaId: _Optional[int] = ..., blueCount: _Optional[int] = ..., blueLevel: _Optional[int] = ..., userIds: _Optional[_Iterable[int]] = ..., state: _Optional[int] = ...) -> None: ...

class GuildMsg(_message.Message):
    __slots__ = ("param1", "param2", "param3", "param4", "param5", "param6")
    PARAM1_FIELD_NUMBER: _ClassVar[int]
    PARAM2_FIELD_NUMBER: _ClassVar[int]
    PARAM3_FIELD_NUMBER: _ClassVar[int]
    PARAM4_FIELD_NUMBER: _ClassVar[int]
    PARAM5_FIELD_NUMBER: _ClassVar[int]
    PARAM6_FIELD_NUMBER: _ClassVar[int]
    param1: int
    param2: int
    param3: str
    param4: str
    param5: bool
    param6: bool
    def __init__(self, param1: _Optional[int] = ..., param2: _Optional[int] = ..., param3: _Optional[str] = ..., param4: _Optional[str] = ..., param5: _Optional[bool] = ..., param6: _Optional[bool] = ...) -> None: ...

class GuildOrderInfoMsg(_message.Message):
    __slots__ = ("order", "id", "name", "count", "power", "chairmanName")
    ORDER_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    POWER_FIELD_NUMBER: _ClassVar[int]
    CHAIRMANNAME_FIELD_NUMBER: _ClassVar[int]
    order: int
    id: int
    name: str
    count: int
    power: int
    chairmanName: str
    def __init__(self, order: _Optional[int] = ..., id: _Optional[int] = ..., name: _Optional[str] = ..., count: _Optional[int] = ..., power: _Optional[int] = ..., chairmanName: _Optional[str] = ...) -> None: ...

class GuildWarInfoListMsg(_message.Message):
    __slots__ = ("guildWarInfos", "userIds")
    GUILDWARINFOS_FIELD_NUMBER: _ClassVar[int]
    USERIDS_FIELD_NUMBER: _ClassVar[int]
    guildWarInfos: _containers.RepeatedCompositeFieldContainer[GuildWarInfoMsg]
    userIds: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, guildWarInfos: _Optional[_Iterable[_Union[GuildWarInfoMsg, _Mapping]]] = ..., userIds: _Optional[_Iterable[int]] = ...) -> None: ...

class GuildWarInfoMsg(_message.Message):
    __slots__ = ("consortiaId", "consrotiaName", "noviceCount", "score", "fightPower", "param1", "param2")
    CONSORTIAID_FIELD_NUMBER: _ClassVar[int]
    CONSROTIANAME_FIELD_NUMBER: _ClassVar[int]
    NOVICECOUNT_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    FIGHTPOWER_FIELD_NUMBER: _ClassVar[int]
    PARAM1_FIELD_NUMBER: _ClassVar[int]
    PARAM2_FIELD_NUMBER: _ClassVar[int]
    consortiaId: int
    consrotiaName: str
    noviceCount: int
    score: int
    fightPower: int
    param1: int
    param2: int
    def __init__(self, consortiaId: _Optional[int] = ..., consrotiaName: _Optional[str] = ..., noviceCount: _Optional[int] = ..., score: _Optional[int] = ..., fightPower: _Optional[int] = ..., param1: _Optional[int] = ..., param2: _Optional[int] = ...) -> None: ...

class HangupAttackMsg(_message.Message):
    __slots__ = ("attackId", "attackName", "defenceId", "defenceName", "op")
    ATTACKID_FIELD_NUMBER: _ClassVar[int]
    ATTACKNAME_FIELD_NUMBER: _ClassVar[int]
    DEFENCEID_FIELD_NUMBER: _ClassVar[int]
    DEFENCENAME_FIELD_NUMBER: _ClassVar[int]
    OP_FIELD_NUMBER: _ClassVar[int]
    attackId: int
    attackName: str
    defenceId: int
    defenceName: int
    op: int
    def __init__(self, attackId: _Optional[int] = ..., attackName: _Optional[str] = ..., defenceId: _Optional[int] = ..., defenceName: _Optional[int] = ..., op: _Optional[int] = ...) -> None: ...

class HangupInfoMsg(_message.Message):
    __slots__ = ("leftWeay", "isStartHangup", "addWeay")
    LEFTWEAY_FIELD_NUMBER: _ClassVar[int]
    ISSTARTHANGUP_FIELD_NUMBER: _ClassVar[int]
    ADDWEAY_FIELD_NUMBER: _ClassVar[int]
    leftWeay: int
    isStartHangup: bool
    addWeay: int
    def __init__(self, leftWeay: _Optional[int] = ..., isStartHangup: _Optional[bool] = ..., addWeay: _Optional[int] = ...) -> None: ...

class HangupStateListMsg(_message.Message):
    __slots__ = ("maxCount", "hangupState")
    MAXCOUNT_FIELD_NUMBER: _ClassVar[int]
    HANGUPSTATE_FIELD_NUMBER: _ClassVar[int]
    maxCount: int
    hangupState: _containers.RepeatedCompositeFieldContainer[HangupStateMsg]
    def __init__(self, maxCount: _Optional[int] = ..., hangupState: _Optional[_Iterable[_Union[HangupStateMsg, _Mapping]]] = ...) -> None: ...

class HangupStateMsg(_message.Message):
    __slots__ = ("curCount", "campaignId")
    CURCOUNT_FIELD_NUMBER: _ClassVar[int]
    CAMPAIGNID_FIELD_NUMBER: _ClassVar[int]
    curCount: int
    campaignId: int
    def __init__(self, curCount: _Optional[int] = ..., campaignId: _Optional[int] = ...) -> None: ...

class HasDataInfo(_message.Message):
    __slots__ = ("userId", "itemId", "counts", "buyDate", "isDiscount")
    USERID_FIELD_NUMBER: _ClassVar[int]
    ITEMID_FIELD_NUMBER: _ClassVar[int]
    COUNTS_FIELD_NUMBER: _ClassVar[int]
    BUYDATE_FIELD_NUMBER: _ClassVar[int]
    ISDISCOUNT_FIELD_NUMBER: _ClassVar[int]
    userId: int
    itemId: int
    counts: int
    buyDate: str
    isDiscount: bool
    def __init__(self, userId: _Optional[int] = ..., itemId: _Optional[int] = ..., counts: _Optional[int] = ..., buyDate: _Optional[str] = ..., isDiscount: _Optional[bool] = ...) -> None: ...

class HeartMsg(_message.Message):
    __slots__ = ("order", "templateId", "options", "result", "optionA", "optionB", "remainTime", "random")
    ORDER_FIELD_NUMBER: _ClassVar[int]
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    OPTIONS_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    OPTIONA_FIELD_NUMBER: _ClassVar[int]
    OPTIONB_FIELD_NUMBER: _ClassVar[int]
    REMAINTIME_FIELD_NUMBER: _ClassVar[int]
    RANDOM_FIELD_NUMBER: _ClassVar[int]
    order: int
    templateId: int
    options: _containers.RepeatedScalarFieldContainer[int]
    result: int
    optionA: int
    optionB: int
    remainTime: int
    random: int
    def __init__(self, order: _Optional[int] = ..., templateId: _Optional[int] = ..., options: _Optional[_Iterable[int]] = ..., result: _Optional[int] = ..., optionA: _Optional[int] = ..., optionB: _Optional[int] = ..., remainTime: _Optional[int] = ..., random: _Optional[int] = ...) -> None: ...

class HelpOverMsg(_message.Message):
    __slots__ = ("result",)
    RESULT_FIELD_NUMBER: _ClassVar[int]
    result: bool
    def __init__(self, result: _Optional[bool] = ...) -> None: ...

class HeroAddPointReqMsg(_message.Message):
    __slots__ = ("powerPoint", "agilityPoint", "intellectPoint", "captainPoint", "physiquePoint", "skillTempId", "type")
    POWERPOINT_FIELD_NUMBER: _ClassVar[int]
    AGILITYPOINT_FIELD_NUMBER: _ClassVar[int]
    INTELLECTPOINT_FIELD_NUMBER: _ClassVar[int]
    CAPTAINPOINT_FIELD_NUMBER: _ClassVar[int]
    PHYSIQUEPOINT_FIELD_NUMBER: _ClassVar[int]
    SKILLTEMPID_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    powerPoint: int
    agilityPoint: int
    intellectPoint: int
    captainPoint: int
    physiquePoint: int
    skillTempId: int
    type: int
    def __init__(self, powerPoint: _Optional[int] = ..., agilityPoint: _Optional[int] = ..., intellectPoint: _Optional[int] = ..., captainPoint: _Optional[int] = ..., physiquePoint: _Optional[int] = ..., skillTempId: _Optional[int] = ..., type: _Optional[int] = ...) -> None: ...

class HeroEquUpdatedMsg(_message.Message):
    __slots__ = ("playerId", "armStr", "clothStr", "wing", "hat", "fashionArm", "fashionCloth", "hide", "appellId")
    PLAYERID_FIELD_NUMBER: _ClassVar[int]
    ARMSTR_FIELD_NUMBER: _ClassVar[int]
    CLOTHSTR_FIELD_NUMBER: _ClassVar[int]
    WING_FIELD_NUMBER: _ClassVar[int]
    HAT_FIELD_NUMBER: _ClassVar[int]
    FASHIONARM_FIELD_NUMBER: _ClassVar[int]
    FASHIONCLOTH_FIELD_NUMBER: _ClassVar[int]
    HIDE_FIELD_NUMBER: _ClassVar[int]
    APPELLID_FIELD_NUMBER: _ClassVar[int]
    playerId: int
    armStr: str
    clothStr: str
    wing: str
    hat: str
    fashionArm: str
    fashionCloth: str
    hide: bool
    appellId: int
    def __init__(self, playerId: _Optional[int] = ..., armStr: _Optional[str] = ..., clothStr: _Optional[str] = ..., wing: _Optional[str] = ..., hat: _Optional[str] = ..., fashionArm: _Optional[str] = ..., fashionCloth: _Optional[str] = ..., hide: _Optional[bool] = ..., appellId: _Optional[int] = ...) -> None: ...

class HeroFastKeyMsg(_message.Message):
    __slots__ = ("fastKey", "setResult")
    FASTKEY_FIELD_NUMBER: _ClassVar[int]
    SETRESULT_FIELD_NUMBER: _ClassVar[int]
    fastKey: str
    setResult: bool
    def __init__(self, fastKey: _Optional[str] = ..., setResult: _Optional[bool] = ...) -> None: ...

class HeroHideFashionReqMsg(_message.Message):
    __slots__ = ("hide",)
    HIDE_FIELD_NUMBER: _ClassVar[int]
    hide: int
    def __init__(self, hide: _Optional[int] = ...) -> None: ...

class HeroMsg(_message.Message):
    __slots__ = ("heroId", "livingId", "userId", "userPics", "tempId", "type", "nickName", "grade", "side", "pos", "maxHp", "initHp", "hp", "initHp2", "hp2", "sp", "slotAvata", "clothAvate", "cloakPath", "hairPath", "captain", "res", "qteTime", "castTime", "pics", "job", "phyAttack", "phyDefence", "magAttack", "magDefence", "forceHit", "parry", "sites", "skillScript", "pawnTempId", "skillId", "attackWound", "hitWound", "attackModel", "starBuffer", "item", "headId", "buffers", "isShow", "serverName", "wingAvata", "trials", "battleDrop", "hatAvata", "fashionArmAvata", "fashionClothAvata", "hide", "appellId", "fireResi", "waterResi", "electResi", "windResi", "darkResi", "lightResi", "followSkills", "changeSkills", "defaultSkills", "awake", "livingId2", "changeSkillId", "fateSkillTempIds", "isChange", "petQuality", "fightCapacity", "reduceResi", "strength", "tenacity", "hasShadow", "marriageSkills", "mateId", "mateServerName", "marSkills", "curturn")
    HEROID_FIELD_NUMBER: _ClassVar[int]
    LIVINGID_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    USERPICS_FIELD_NUMBER: _ClassVar[int]
    TEMPID_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    GRADE_FIELD_NUMBER: _ClassVar[int]
    SIDE_FIELD_NUMBER: _ClassVar[int]
    POS_FIELD_NUMBER: _ClassVar[int]
    MAXHP_FIELD_NUMBER: _ClassVar[int]
    INITHP_FIELD_NUMBER: _ClassVar[int]
    HP_FIELD_NUMBER: _ClassVar[int]
    INITHP2_FIELD_NUMBER: _ClassVar[int]
    HP2_FIELD_NUMBER: _ClassVar[int]
    SP_FIELD_NUMBER: _ClassVar[int]
    SLOTAVATA_FIELD_NUMBER: _ClassVar[int]
    CLOTHAVATE_FIELD_NUMBER: _ClassVar[int]
    CLOAKPATH_FIELD_NUMBER: _ClassVar[int]
    HAIRPATH_FIELD_NUMBER: _ClassVar[int]
    CAPTAIN_FIELD_NUMBER: _ClassVar[int]
    RES_FIELD_NUMBER: _ClassVar[int]
    QTETIME_FIELD_NUMBER: _ClassVar[int]
    CASTTIME_FIELD_NUMBER: _ClassVar[int]
    PICS_FIELD_NUMBER: _ClassVar[int]
    JOB_FIELD_NUMBER: _ClassVar[int]
    PHYATTACK_FIELD_NUMBER: _ClassVar[int]
    PHYDEFENCE_FIELD_NUMBER: _ClassVar[int]
    MAGATTACK_FIELD_NUMBER: _ClassVar[int]
    MAGDEFENCE_FIELD_NUMBER: _ClassVar[int]
    FORCEHIT_FIELD_NUMBER: _ClassVar[int]
    PARRY_FIELD_NUMBER: _ClassVar[int]
    SITES_FIELD_NUMBER: _ClassVar[int]
    SKILLSCRIPT_FIELD_NUMBER: _ClassVar[int]
    PAWNTEMPID_FIELD_NUMBER: _ClassVar[int]
    SKILLID_FIELD_NUMBER: _ClassVar[int]
    ATTACKWOUND_FIELD_NUMBER: _ClassVar[int]
    HITWOUND_FIELD_NUMBER: _ClassVar[int]
    ATTACKMODEL_FIELD_NUMBER: _ClassVar[int]
    STARBUFFER_FIELD_NUMBER: _ClassVar[int]
    ITEM_FIELD_NUMBER: _ClassVar[int]
    HEADID_FIELD_NUMBER: _ClassVar[int]
    BUFFERS_FIELD_NUMBER: _ClassVar[int]
    ISSHOW_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    WINGAVATA_FIELD_NUMBER: _ClassVar[int]
    TRIALS_FIELD_NUMBER: _ClassVar[int]
    BATTLEDROP_FIELD_NUMBER: _ClassVar[int]
    HATAVATA_FIELD_NUMBER: _ClassVar[int]
    FASHIONARMAVATA_FIELD_NUMBER: _ClassVar[int]
    FASHIONCLOTHAVATA_FIELD_NUMBER: _ClassVar[int]
    HIDE_FIELD_NUMBER: _ClassVar[int]
    APPELLID_FIELD_NUMBER: _ClassVar[int]
    FIRERESI_FIELD_NUMBER: _ClassVar[int]
    WATERRESI_FIELD_NUMBER: _ClassVar[int]
    ELECTRESI_FIELD_NUMBER: _ClassVar[int]
    WINDRESI_FIELD_NUMBER: _ClassVar[int]
    DARKRESI_FIELD_NUMBER: _ClassVar[int]
    LIGHTRESI_FIELD_NUMBER: _ClassVar[int]
    FOLLOWSKILLS_FIELD_NUMBER: _ClassVar[int]
    CHANGESKILLS_FIELD_NUMBER: _ClassVar[int]
    DEFAULTSKILLS_FIELD_NUMBER: _ClassVar[int]
    AWAKE_FIELD_NUMBER: _ClassVar[int]
    LIVINGID2_FIELD_NUMBER: _ClassVar[int]
    CHANGESKILLID_FIELD_NUMBER: _ClassVar[int]
    FATESKILLTEMPIDS_FIELD_NUMBER: _ClassVar[int]
    ISCHANGE_FIELD_NUMBER: _ClassVar[int]
    PETQUALITY_FIELD_NUMBER: _ClassVar[int]
    FIGHTCAPACITY_FIELD_NUMBER: _ClassVar[int]
    REDUCERESI_FIELD_NUMBER: _ClassVar[int]
    STRENGTH_FIELD_NUMBER: _ClassVar[int]
    TENACITY_FIELD_NUMBER: _ClassVar[int]
    HASSHADOW_FIELD_NUMBER: _ClassVar[int]
    MARRIAGESKILLS_FIELD_NUMBER: _ClassVar[int]
    MATEID_FIELD_NUMBER: _ClassVar[int]
    MATESERVERNAME_FIELD_NUMBER: _ClassVar[int]
    MARSKILLS_FIELD_NUMBER: _ClassVar[int]
    CURTURN_FIELD_NUMBER: _ClassVar[int]
    heroId: int
    livingId: int
    userId: int
    userPics: int
    tempId: int
    type: int
    nickName: str
    grade: int
    side: int
    pos: int
    maxHp: int
    initHp: int
    hp: int
    initHp2: int
    hp2: int
    sp: int
    slotAvata: str
    clothAvate: str
    cloakPath: str
    hairPath: str
    captain: int
    res: str
    qteTime: int
    castTime: int
    pics: int
    job: int
    phyAttack: int
    phyDefence: int
    magAttack: int
    magDefence: int
    forceHit: int
    parry: int
    sites: int
    skillScript: str
    pawnTempId: int
    skillId: _containers.RepeatedScalarFieldContainer[int]
    attackWound: int
    hitWound: int
    attackModel: int
    starBuffer: _containers.RepeatedCompositeFieldContainer[StarBufferMsg]
    item: _containers.RepeatedCompositeFieldContainer[BattleItemMsg]
    headId: int
    buffers: _containers.RepeatedCompositeFieldContainer[BufferMsg]
    isShow: bool
    serverName: str
    wingAvata: str
    trials: _containers.RepeatedCompositeFieldContainer[TrialInfoMsg]
    battleDrop: _containers.RepeatedCompositeFieldContainer[BaseItemMsg]
    hatAvata: str
    fashionArmAvata: str
    fashionClothAvata: str
    hide: bool
    appellId: int
    fireResi: int
    waterResi: int
    electResi: int
    windResi: int
    darkResi: int
    lightResi: int
    followSkills: str
    changeSkills: str
    defaultSkills: str
    awake: int
    livingId2: int
    changeSkillId: _containers.RepeatedScalarFieldContainer[int]
    fateSkillTempIds: str
    isChange: bool
    petQuality: int
    fightCapacity: int
    reduceResi: int
    strength: int
    tenacity: int
    hasShadow: bool
    marriageSkills: _containers.RepeatedScalarFieldContainer[int]
    mateId: int
    mateServerName: str
    marSkills: _containers.RepeatedCompositeFieldContainer[TrialInfoMsg]
    curturn: int
    def __init__(self, heroId: _Optional[int] = ..., livingId: _Optional[int] = ..., userId: _Optional[int] = ..., userPics: _Optional[int] = ..., tempId: _Optional[int] = ..., type: _Optional[int] = ..., nickName: _Optional[str] = ..., grade: _Optional[int] = ..., side: _Optional[int] = ..., pos: _Optional[int] = ..., maxHp: _Optional[int] = ..., initHp: _Optional[int] = ..., hp: _Optional[int] = ..., initHp2: _Optional[int] = ..., hp2: _Optional[int] = ..., sp: _Optional[int] = ..., slotAvata: _Optional[str] = ..., clothAvate: _Optional[str] = ..., cloakPath: _Optional[str] = ..., hairPath: _Optional[str] = ..., captain: _Optional[int] = ..., res: _Optional[str] = ..., qteTime: _Optional[int] = ..., castTime: _Optional[int] = ..., pics: _Optional[int] = ..., job: _Optional[int] = ..., phyAttack: _Optional[int] = ..., phyDefence: _Optional[int] = ..., magAttack: _Optional[int] = ..., magDefence: _Optional[int] = ..., forceHit: _Optional[int] = ..., parry: _Optional[int] = ..., sites: _Optional[int] = ..., skillScript: _Optional[str] = ..., pawnTempId: _Optional[int] = ..., skillId: _Optional[_Iterable[int]] = ..., attackWound: _Optional[int] = ..., hitWound: _Optional[int] = ..., attackModel: _Optional[int] = ..., starBuffer: _Optional[_Iterable[_Union[StarBufferMsg, _Mapping]]] = ..., item: _Optional[_Iterable[_Union[BattleItemMsg, _Mapping]]] = ..., headId: _Optional[int] = ..., buffers: _Optional[_Iterable[_Union[BufferMsg, _Mapping]]] = ..., isShow: _Optional[bool] = ..., serverName: _Optional[str] = ..., wingAvata: _Optional[str] = ..., trials: _Optional[_Iterable[_Union[TrialInfoMsg, _Mapping]]] = ..., battleDrop: _Optional[_Iterable[_Union[BaseItemMsg, _Mapping]]] = ..., hatAvata: _Optional[str] = ..., fashionArmAvata: _Optional[str] = ..., fashionClothAvata: _Optional[str] = ..., hide: _Optional[bool] = ..., appellId: _Optional[int] = ..., fireResi: _Optional[int] = ..., waterResi: _Optional[int] = ..., electResi: _Optional[int] = ..., windResi: _Optional[int] = ..., darkResi: _Optional[int] = ..., lightResi: _Optional[int] = ..., followSkills: _Optional[str] = ..., changeSkills: _Optional[str] = ..., defaultSkills: _Optional[str] = ..., awake: _Optional[int] = ..., livingId2: _Optional[int] = ..., changeSkillId: _Optional[_Iterable[int]] = ..., fateSkillTempIds: _Optional[str] = ..., isChange: _Optional[bool] = ..., petQuality: _Optional[int] = ..., fightCapacity: _Optional[int] = ..., reduceResi: _Optional[int] = ..., strength: _Optional[int] = ..., tenacity: _Optional[int] = ..., hasShadow: _Optional[bool] = ..., marriageSkills: _Optional[_Iterable[int]] = ..., mateId: _Optional[int] = ..., mateServerName: _Optional[str] = ..., marSkills: _Optional[_Iterable[_Union[TrialInfoMsg, _Mapping]]] = ..., curturn: _Optional[int] = ...) -> None: ...

class HeroOrderMsg(_message.Message):
    __slots__ = ("battleId", "heroIndexId", "skillId", "result", "castTime", "qteTime", "targetIndexs")
    BATTLEID_FIELD_NUMBER: _ClassVar[int]
    HEROINDEXID_FIELD_NUMBER: _ClassVar[int]
    SKILLID_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    CASTTIME_FIELD_NUMBER: _ClassVar[int]
    QTETIME_FIELD_NUMBER: _ClassVar[int]
    TARGETINDEXS_FIELD_NUMBER: _ClassVar[int]
    battleId: str
    heroIndexId: int
    skillId: int
    result: int
    castTime: int
    qteTime: int
    targetIndexs: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, battleId: _Optional[str] = ..., heroIndexId: _Optional[int] = ..., skillId: _Optional[int] = ..., result: _Optional[int] = ..., castTime: _Optional[int] = ..., qteTime: _Optional[int] = ..., targetIndexs: _Optional[_Iterable[int]] = ...) -> None: ...

class HeroRuneInfoMsg(_message.Message):
    __slots__ = ("runeId", "runeGp", "swallowCount")
    RUNEID_FIELD_NUMBER: _ClassVar[int]
    RUNEGP_FIELD_NUMBER: _ClassVar[int]
    SWALLOWCOUNT_FIELD_NUMBER: _ClassVar[int]
    runeId: int
    runeGp: int
    swallowCount: int
    def __init__(self, runeId: _Optional[int] = ..., runeGp: _Optional[int] = ..., swallowCount: _Optional[int] = ...) -> None: ...

class HeroRuneMsg(_message.Message):
    __slots__ = ("userId", "runeinfo", "runeKey")
    USERID_FIELD_NUMBER: _ClassVar[int]
    RUNEINFO_FIELD_NUMBER: _ClassVar[int]
    RUNEKEY_FIELD_NUMBER: _ClassVar[int]
    userId: int
    runeinfo: _containers.RepeatedCompositeFieldContainer[HeroRuneInfoMsg]
    runeKey: str
    def __init__(self, userId: _Optional[int] = ..., runeinfo: _Optional[_Iterable[_Union[HeroRuneInfoMsg, _Mapping]]] = ..., runeKey: _Optional[str] = ...) -> None: ...

class HeroRuneOpMsg(_message.Message):
    __slots__ = ("userId", "runeId", "runeKey", "learnRunePos", "learnRuneCount", "opType", "opResult", "runeInfo", "count")
    USERID_FIELD_NUMBER: _ClassVar[int]
    RUNEID_FIELD_NUMBER: _ClassVar[int]
    RUNEKEY_FIELD_NUMBER: _ClassVar[int]
    LEARNRUNEPOS_FIELD_NUMBER: _ClassVar[int]
    LEARNRUNECOUNT_FIELD_NUMBER: _ClassVar[int]
    OPTYPE_FIELD_NUMBER: _ClassVar[int]
    OPRESULT_FIELD_NUMBER: _ClassVar[int]
    RUNEINFO_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    userId: int
    runeId: int
    runeKey: str
    learnRunePos: int
    learnRuneCount: int
    opType: int
    opResult: bool
    runeInfo: HeroRuneMsg
    count: int
    def __init__(self, userId: _Optional[int] = ..., runeId: _Optional[int] = ..., runeKey: _Optional[str] = ..., learnRunePos: _Optional[int] = ..., learnRuneCount: _Optional[int] = ..., opType: _Optional[int] = ..., opResult: _Optional[bool] = ..., runeInfo: _Optional[_Union[HeroRuneMsg, _Mapping]] = ..., count: _Optional[int] = ...) -> None: ...

class HeroSkillChangeMsg(_message.Message):
    __slots__ = ("index", "payType", "result")
    INDEX_FIELD_NUMBER: _ClassVar[int]
    PAYTYPE_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    index: int
    payType: int
    result: bool
    def __init__(self, index: _Optional[int] = ..., payType: _Optional[int] = ..., result: _Optional[bool] = ...) -> None: ...

class HeroSkillInfoMsg(_message.Message):
    __slots__ = ("skillPoint", "skillScript", "skillSet")
    SKILLPOINT_FIELD_NUMBER: _ClassVar[int]
    SKILLSCRIPT_FIELD_NUMBER: _ClassVar[int]
    SKILLSET_FIELD_NUMBER: _ClassVar[int]
    skillPoint: int
    skillScript: str
    skillSet: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, skillPoint: _Optional[int] = ..., skillScript: _Optional[str] = ..., skillSet: _Optional[_Iterable[int]] = ...) -> None: ...

class HeroSkillResetMsg(_message.Message):
    __slots__ = ("payType",)
    PAYTYPE_FIELD_NUMBER: _ClassVar[int]
    payType: int
    def __init__(self, payType: _Optional[int] = ...) -> None: ...

class HeroTalentMsg(_message.Message):
    __slots__ = ("userId", "talentPoint", "talentGrade")
    USERID_FIELD_NUMBER: _ClassVar[int]
    TALENTPOINT_FIELD_NUMBER: _ClassVar[int]
    TALENTGRADE_FIELD_NUMBER: _ClassVar[int]
    userId: int
    talentPoint: int
    talentGrade: int
    def __init__(self, userId: _Optional[int] = ..., talentPoint: _Optional[int] = ..., talentGrade: _Optional[int] = ...) -> None: ...

class HeroWatchMsg(_message.Message):
    __slots__ = ("userId", "watchInfo")
    USERID_FIELD_NUMBER: _ClassVar[int]
    WATCHINFO_FIELD_NUMBER: _ClassVar[int]
    userId: int
    watchInfo: _containers.RepeatedCompositeFieldContainer[WatchInfoMsg]
    def __init__(self, userId: _Optional[int] = ..., watchInfo: _Optional[_Iterable[_Union[WatchInfoMsg, _Mapping]]] = ...) -> None: ...

class HeroWatchOpMsg(_message.Message):
    __slots__ = ("opType", "gridType", "gridPos", "jionPos", "itemPos")
    OPTYPE_FIELD_NUMBER: _ClassVar[int]
    GRIDTYPE_FIELD_NUMBER: _ClassVar[int]
    GRIDPOS_FIELD_NUMBER: _ClassVar[int]
    JIONPOS_FIELD_NUMBER: _ClassVar[int]
    ITEMPOS_FIELD_NUMBER: _ClassVar[int]
    opType: int
    gridType: int
    gridPos: int
    jionPos: int
    itemPos: int
    def __init__(self, opType: _Optional[int] = ..., gridType: _Optional[int] = ..., gridPos: _Optional[int] = ..., jionPos: _Optional[int] = ..., itemPos: _Optional[int] = ...) -> None: ...

class HurtDataMsg(_message.Message):
    __slots__ = ("affecteId", "value", "serverName", "damageType", "leftTime")
    AFFECTEID_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    DAMAGETYPE_FIELD_NUMBER: _ClassVar[int]
    LEFTTIME_FIELD_NUMBER: _ClassVar[int]
    affecteId: int
    value: int
    serverName: str
    damageType: int
    leftTime: int
    def __init__(self, affecteId: _Optional[int] = ..., value: _Optional[int] = ..., serverName: _Optional[str] = ..., damageType: _Optional[int] = ..., leftTime: _Optional[int] = ...) -> None: ...

class HurtOrderMsg(_message.Message):
    __slots__ = ("userId", "hurt", "isInAltar")
    USERID_FIELD_NUMBER: _ClassVar[int]
    HURT_FIELD_NUMBER: _ClassVar[int]
    ISINALTAR_FIELD_NUMBER: _ClassVar[int]
    userId: int
    hurt: int
    isInAltar: bool
    def __init__(self, userId: _Optional[int] = ..., hurt: _Optional[int] = ..., isInAltar: _Optional[bool] = ...) -> None: ...

class IconNumMsg(_message.Message):
    __slots__ = ("type", "intValue1")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    INTVALUE1_FIELD_NUMBER: _ClassVar[int]
    type: int
    intValue1: int
    def __init__(self, type: _Optional[int] = ..., intValue1: _Optional[int] = ...) -> None: ...

class IconNumMsgList(_message.Message):
    __slots__ = ("op", "list")
    OP_FIELD_NUMBER: _ClassVar[int]
    LIST_FIELD_NUMBER: _ClassVar[int]
    op: int
    list: _containers.RepeatedCompositeFieldContainer[IconNumMsg]
    def __init__(self, op: _Optional[int] = ..., list: _Optional[_Iterable[_Union[IconNumMsg, _Mapping]]] = ...) -> None: ...

class InfoReqMsg(_message.Message):
    __slots__ = ("otherId",)
    OTHERID_FIELD_NUMBER: _ClassVar[int]
    FROM_FIELD_NUMBER: _ClassVar[int]
    otherId: int
    def __init__(self, otherId: _Optional[int] = ..., **kwargs) -> None: ...

class InfoRspMsg(_message.Message):
    __slots__ = ("info",)
    INFO_FIELD_NUMBER: _ClassVar[int]
    FROM_FIELD_NUMBER: _ClassVar[int]
    info: SimplePlayerInfoMsg
    def __init__(self, info: _Optional[_Union[SimplePlayerInfoMsg, _Mapping]] = ..., **kwargs) -> None: ...

class InviteTeamMsg(_message.Message):
    __slots__ = ("teamId", "inviterId", "inviterName")
    TEAMID_FIELD_NUMBER: _ClassVar[int]
    INVITERID_FIELD_NUMBER: _ClassVar[int]
    INVITERNAME_FIELD_NUMBER: _ClassVar[int]
    teamId: int
    inviterId: int
    inviterName: str
    def __init__(self, teamId: _Optional[int] = ..., inviterId: _Optional[int] = ..., inviterName: _Optional[str] = ...) -> None: ...

class ItemBufferRspMsg(_message.Message):
    __slots__ = ("bufferData",)
    BUFFERDATA_FIELD_NUMBER: _ClassVar[int]
    bufferData: _containers.RepeatedCompositeFieldContainer[BufferDataMsg]
    def __init__(self, bufferData: _Optional[_Iterable[_Union[BufferDataMsg, _Mapping]]] = ...) -> None: ...

class ItemInfoMsg(_message.Message):
    __slots__ = ("id", "templateId", "pos", "exist", "objectId", "bagType", "bind", "used", "validDate", "beginDate", "count", "attack", "defence", "agility", "ability", "captain", "strengthenGrade", "join_1", "join_2", "join_3", "join_4", "randomSkill_1", "randomSkill_2", "randomSkill_3", "randomSkill_4", "randomSkill_5", "isNew", "userId", "property1", "strength", "tenacity", "appraisalSkill", "isLocked", "mouldGrade", "blessValue")
    ID_FIELD_NUMBER: _ClassVar[int]
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    POS_FIELD_NUMBER: _ClassVar[int]
    EXIST_FIELD_NUMBER: _ClassVar[int]
    OBJECTID_FIELD_NUMBER: _ClassVar[int]
    BAGTYPE_FIELD_NUMBER: _ClassVar[int]
    BIND_FIELD_NUMBER: _ClassVar[int]
    USED_FIELD_NUMBER: _ClassVar[int]
    VALIDDATE_FIELD_NUMBER: _ClassVar[int]
    BEGINDATE_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    ATTACK_FIELD_NUMBER: _ClassVar[int]
    DEFENCE_FIELD_NUMBER: _ClassVar[int]
    AGILITY_FIELD_NUMBER: _ClassVar[int]
    ABILITY_FIELD_NUMBER: _ClassVar[int]
    CAPTAIN_FIELD_NUMBER: _ClassVar[int]
    STRENGTHENGRADE_FIELD_NUMBER: _ClassVar[int]
    JOIN_1_FIELD_NUMBER: _ClassVar[int]
    JOIN_2_FIELD_NUMBER: _ClassVar[int]
    JOIN_3_FIELD_NUMBER: _ClassVar[int]
    JOIN_4_FIELD_NUMBER: _ClassVar[int]
    RANDOMSKILL_1_FIELD_NUMBER: _ClassVar[int]
    RANDOMSKILL_2_FIELD_NUMBER: _ClassVar[int]
    RANDOMSKILL_3_FIELD_NUMBER: _ClassVar[int]
    RANDOMSKILL_4_FIELD_NUMBER: _ClassVar[int]
    RANDOMSKILL_5_FIELD_NUMBER: _ClassVar[int]
    ISNEW_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    PROPERTY1_FIELD_NUMBER: _ClassVar[int]
    STRENGTH_FIELD_NUMBER: _ClassVar[int]
    TENACITY_FIELD_NUMBER: _ClassVar[int]
    APPRAISALSKILL_FIELD_NUMBER: _ClassVar[int]
    ISLOCKED_FIELD_NUMBER: _ClassVar[int]
    MOULDGRADE_FIELD_NUMBER: _ClassVar[int]
    BLESSVALUE_FIELD_NUMBER: _ClassVar[int]
    id: int
    templateId: int
    pos: int
    exist: bool
    objectId: int
    bagType: int
    bind: bool
    used: bool
    validDate: int
    beginDate: str
    count: int
    attack: int
    defence: int
    agility: int
    ability: int
    captain: int
    strengthenGrade: int
    join_1: int
    join_2: int
    join_3: int
    join_4: int
    randomSkill_1: int
    randomSkill_2: int
    randomSkill_3: int
    randomSkill_4: int
    randomSkill_5: int
    isNew: bool
    userId: int
    property1: str
    strength: int
    tenacity: int
    appraisalSkill: int
    isLocked: bool
    mouldGrade: int
    blessValue: int
    def __init__(self, id: _Optional[int] = ..., templateId: _Optional[int] = ..., pos: _Optional[int] = ..., exist: _Optional[bool] = ..., objectId: _Optional[int] = ..., bagType: _Optional[int] = ..., bind: _Optional[bool] = ..., used: _Optional[bool] = ..., validDate: _Optional[int] = ..., beginDate: _Optional[str] = ..., count: _Optional[int] = ..., attack: _Optional[int] = ..., defence: _Optional[int] = ..., agility: _Optional[int] = ..., ability: _Optional[int] = ..., captain: _Optional[int] = ..., strengthenGrade: _Optional[int] = ..., join_1: _Optional[int] = ..., join_2: _Optional[int] = ..., join_3: _Optional[int] = ..., join_4: _Optional[int] = ..., randomSkill_1: _Optional[int] = ..., randomSkill_2: _Optional[int] = ..., randomSkill_3: _Optional[int] = ..., randomSkill_4: _Optional[int] = ..., randomSkill_5: _Optional[int] = ..., isNew: _Optional[bool] = ..., userId: _Optional[int] = ..., property1: _Optional[str] = ..., strength: _Optional[int] = ..., tenacity: _Optional[int] = ..., appraisalSkill: _Optional[int] = ..., isLocked: _Optional[bool] = ..., mouldGrade: _Optional[int] = ..., blessValue: _Optional[int] = ...) -> None: ...

class ItemInfoReqMsg(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, id: _Optional[_Iterable[int]] = ...) -> None: ...

class ItemInfoRspMsg(_message.Message):
    __slots__ = ("itemInfo",)
    ITEMINFO_FIELD_NUMBER: _ClassVar[int]
    itemInfo: _containers.RepeatedCompositeFieldContainer[ItemInfoMsg]
    def __init__(self, itemInfo: _Optional[_Iterable[_Union[ItemInfoMsg, _Mapping]]] = ...) -> None: ...

class ItemMoveUpdateMsg(_message.Message):
    __slots__ = ("changeType", "changeObjId", "changePos", "item")
    CHANGETYPE_FIELD_NUMBER: _ClassVar[int]
    CHANGEOBJID_FIELD_NUMBER: _ClassVar[int]
    CHANGEPOS_FIELD_NUMBER: _ClassVar[int]
    ITEM_FIELD_NUMBER: _ClassVar[int]
    changeType: int
    changeObjId: int
    changePos: int
    item: ItemInfoMsg
    def __init__(self, changeType: _Optional[int] = ..., changeObjId: _Optional[int] = ..., changePos: _Optional[int] = ..., item: _Optional[_Union[ItemInfoMsg, _Mapping]] = ...) -> None: ...

class ItemMovedListMsg(_message.Message):
    __slots__ = ("moved",)
    MOVED_FIELD_NUMBER: _ClassVar[int]
    moved: _containers.RepeatedCompositeFieldContainer[ItemMoveUpdateMsg]
    def __init__(self, moved: _Optional[_Iterable[_Union[ItemMoveUpdateMsg, _Mapping]]] = ...) -> None: ...

class ItemRemoveMsg(_message.Message):
    __slots__ = ("bagType", "pos")
    BAGTYPE_FIELD_NUMBER: _ClassVar[int]
    POS_FIELD_NUMBER: _ClassVar[int]
    bagType: int
    pos: int
    def __init__(self, bagType: _Optional[int] = ..., pos: _Optional[int] = ...) -> None: ...

class ItemReqMsg(_message.Message):
    __slots__ = ("beginBagType", "beginObjId", "beginPos", "endBagType", "endObjId", "endPos", "count", "objectId")
    BEGINBAGTYPE_FIELD_NUMBER: _ClassVar[int]
    BEGINOBJID_FIELD_NUMBER: _ClassVar[int]
    BEGINPOS_FIELD_NUMBER: _ClassVar[int]
    ENDBAGTYPE_FIELD_NUMBER: _ClassVar[int]
    ENDOBJID_FIELD_NUMBER: _ClassVar[int]
    ENDPOS_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    OBJECTID_FIELD_NUMBER: _ClassVar[int]
    beginBagType: int
    beginObjId: int
    beginPos: int
    endBagType: int
    endObjId: int
    endPos: int
    count: int
    objectId: int
    def __init__(self, beginBagType: _Optional[int] = ..., beginObjId: _Optional[int] = ..., beginPos: _Optional[int] = ..., endBagType: _Optional[int] = ..., endObjId: _Optional[int] = ..., endPos: _Optional[int] = ..., count: _Optional[int] = ..., objectId: _Optional[int] = ...) -> None: ...

class ItemSellReqMsg(_message.Message):
    __slots__ = ("selledItemInfos",)
    SELLEDITEMINFOS_FIELD_NUMBER: _ClassVar[int]
    selledItemInfos: _containers.RepeatedCompositeFieldContainer[SelledItemInfo]
    def __init__(self, selledItemInfos: _Optional[_Iterable[_Union[SelledItemInfo, _Mapping]]] = ...) -> None: ...

class ItemSmithyMsg(_message.Message):
    __slots__ = ("composeId",)
    COMPOSEID_FIELD_NUMBER: _ClassVar[int]
    composeId: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, composeId: _Optional[_Iterable[int]] = ...) -> None: ...

class ItemTemplate(_message.Message):
    __slots__ = ("templateId", "count")
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    templateId: int
    count: int
    def __init__(self, templateId: _Optional[int] = ..., count: _Optional[int] = ...) -> None: ...

class ItemUseMsg(_message.Message):
    __slots__ = ("pos", "count", "bagType", "battleId", "friendId")
    POS_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    BAGTYPE_FIELD_NUMBER: _ClassVar[int]
    BATTLEID_FIELD_NUMBER: _ClassVar[int]
    FRIENDID_FIELD_NUMBER: _ClassVar[int]
    pos: int
    count: int
    bagType: int
    battleId: str
    friendId: int
    def __init__(self, pos: _Optional[int] = ..., count: _Optional[int] = ..., bagType: _Optional[int] = ..., battleId: _Optional[str] = ..., friendId: _Optional[int] = ...) -> None: ...

class ItemUseResultMsg(_message.Message):
    __slots__ = ("uItemId", "bagPos", "count", "result", "livingId", "tempId", "type")
    UITEMID_FIELD_NUMBER: _ClassVar[int]
    BAGPOS_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    LIVINGID_FIELD_NUMBER: _ClassVar[int]
    TEMPID_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    uItemId: int
    bagPos: int
    count: int
    result: int
    livingId: int
    tempId: int
    type: int
    def __init__(self, uItemId: _Optional[int] = ..., bagPos: _Optional[int] = ..., count: _Optional[int] = ..., result: _Optional[int] = ..., livingId: _Optional[int] = ..., tempId: _Optional[int] = ..., type: _Optional[int] = ...) -> None: ...

class ItemUseStoreReqMsg(_message.Message):
    __slots__ = ("count",)
    COUNT_FIELD_NUMBER: _ClassVar[int]
    count: int
    def __init__(self, count: _Optional[int] = ...) -> None: ...

class ItemUseStoreRspMsg(_message.Message):
    __slots__ = ("result",)
    RESULT_FIELD_NUMBER: _ClassVar[int]
    result: bool
    def __init__(self, result: _Optional[bool] = ...) -> None: ...

class KillPlayerRspMsg(_message.Message):
    __slots__ = ("roomId", "killedPlayerId")
    ROOMID_FIELD_NUMBER: _ClassVar[int]
    KILLEDPLAYERID_FIELD_NUMBER: _ClassVar[int]
    roomId: int
    killedPlayerId: int
    def __init__(self, roomId: _Optional[int] = ..., killedPlayerId: _Optional[int] = ...) -> None: ...

class KingContractBuyMsg(_message.Message):
    __slots__ = ("ids", "__use", "friendId", "friendname")
    IDS_FIELD_NUMBER: _ClassVar[int]
    __USE_FIELD_NUMBER: _ClassVar[int]
    FRIENDID_FIELD_NUMBER: _ClassVar[int]
    FRIENDNAME_FIELD_NUMBER: _ClassVar[int]
    ids: _containers.RepeatedScalarFieldContainer[int]
    __use: bool
    friendId: int
    friendname: str
    def __init__(self, ids: _Optional[_Iterable[int]] = ..., __use: _Optional[bool] = ..., friendId: _Optional[int] = ..., friendname: _Optional[str] = ...) -> None: ...

class KingContractInfoMsg(_message.Message):
    __slots__ = ("contractId", "endData")
    CONTRACTID_FIELD_NUMBER: _ClassVar[int]
    ENDDATA_FIELD_NUMBER: _ClassVar[int]
    contractId: int
    endData: str
    def __init__(self, contractId: _Optional[int] = ..., endData: _Optional[str] = ...) -> None: ...

class KingContractMsg(_message.Message):
    __slots__ = ("kingContractInfos",)
    KINGCONTRACTINFOS_FIELD_NUMBER: _ClassVar[int]
    kingContractInfos: _containers.RepeatedCompositeFieldContainer[KingContractInfoMsg]
    def __init__(self, kingContractInfos: _Optional[_Iterable[_Union[KingContractInfoMsg, _Mapping]]] = ...) -> None: ...

class KingTowerInfoMsg(_message.Message):
    __slots__ = ("enterCount", "currentIndex", "maxIndex", "campaignId", "currentStep", "rewardCount")
    ENTERCOUNT_FIELD_NUMBER: _ClassVar[int]
    CURRENTINDEX_FIELD_NUMBER: _ClassVar[int]
    MAXINDEX_FIELD_NUMBER: _ClassVar[int]
    CAMPAIGNID_FIELD_NUMBER: _ClassVar[int]
    CURRENTSTEP_FIELD_NUMBER: _ClassVar[int]
    REWARDCOUNT_FIELD_NUMBER: _ClassVar[int]
    enterCount: int
    currentIndex: int
    maxIndex: int
    campaignId: int
    currentStep: int
    rewardCount: int
    def __init__(self, enterCount: _Optional[int] = ..., currentIndex: _Optional[int] = ..., maxIndex: _Optional[int] = ..., campaignId: _Optional[int] = ..., currentStep: _Optional[int] = ..., rewardCount: _Optional[int] = ...) -> None: ...

class LeadRewardMsg(_message.Message):
    __slots__ = ("op", "templateId", "leadExtractTimes", "count")
    OP_FIELD_NUMBER: _ClassVar[int]
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    LEADEXTRACTTIMES_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    op: int
    templateId: int
    leadExtractTimes: int
    count: int
    def __init__(self, op: _Optional[int] = ..., templateId: _Optional[int] = ..., leadExtractTimes: _Optional[int] = ..., count: _Optional[int] = ...) -> None: ...

class LeedData(_message.Message):
    __slots__ = ("templateId", "userId", "currentCount", "beginDate", "isComplete")
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    CURRENTCOUNT_FIELD_NUMBER: _ClassVar[int]
    BEGINDATE_FIELD_NUMBER: _ClassVar[int]
    ISCOMPLETE_FIELD_NUMBER: _ClassVar[int]
    templateId: int
    userId: int
    currentCount: int
    beginDate: str
    isComplete: bool
    def __init__(self, templateId: _Optional[int] = ..., userId: _Optional[int] = ..., currentCount: _Optional[int] = ..., beginDate: _Optional[str] = ..., isComplete: _Optional[bool] = ...) -> None: ...

class LeedFinishedReqMsg(_message.Message):
    __slots__ = ("site",)
    SITE_FIELD_NUMBER: _ClassVar[int]
    site: int
    def __init__(self, site: _Optional[int] = ...) -> None: ...

class LeedFinishedRspMsg(_message.Message):
    __slots__ = ("result", "site", "leedProcess")
    RESULT_FIELD_NUMBER: _ClassVar[int]
    SITE_FIELD_NUMBER: _ClassVar[int]
    LEEDPROCESS_FIELD_NUMBER: _ClassVar[int]
    result: bool
    site: int
    leedProcess: int
    def __init__(self, result: _Optional[bool] = ..., site: _Optional[int] = ..., leedProcess: _Optional[int] = ...) -> None: ...

class LeedUpdatedRspMsg(_message.Message):
    __slots__ = ("leed", "leedProcess", "totalNum")
    LEED_FIELD_NUMBER: _ClassVar[int]
    LEEDPROCESS_FIELD_NUMBER: _ClassVar[int]
    TOTALNUM_FIELD_NUMBER: _ClassVar[int]
    leed: _containers.RepeatedCompositeFieldContainer[LeedData]
    leedProcess: int
    totalNum: int
    def __init__(self, leed: _Optional[_Iterable[_Union[LeedData, _Mapping]]] = ..., leedProcess: _Optional[int] = ..., totalNum: _Optional[int] = ...) -> None: ...

class LoadFarmRsp(_message.Message):
    __slots__ = ("friendFarmState", "farm", "farmLog")
    FRIENDFARMSTATE_FIELD_NUMBER: _ClassVar[int]
    FARM_FIELD_NUMBER: _ClassVar[int]
    FARMLOG_FIELD_NUMBER: _ClassVar[int]
    friendFarmState: _containers.RepeatedCompositeFieldContainer[FriendFarmStateMsg]
    farm: FarmInfoRspMsg
    farmLog: _containers.RepeatedCompositeFieldContainer[FarmLogRsp]
    def __init__(self, friendFarmState: _Optional[_Iterable[_Union[FriendFarmStateMsg, _Mapping]]] = ..., farm: _Optional[_Union[FarmInfoRspMsg, _Mapping]] = ..., farmLog: _Optional[_Iterable[_Union[FarmLogRsp, _Mapping]]] = ...) -> None: ...

class LoadOverMsg(_message.Message):
    __slots__ = ("armyId", "battleId", "serverName")
    ARMYID_FIELD_NUMBER: _ClassVar[int]
    BATTLEID_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    armyId: int
    battleId: str
    serverName: str
    def __init__(self, armyId: _Optional[int] = ..., battleId: _Optional[str] = ..., serverName: _Optional[str] = ...) -> None: ...

class LockAndUnlockMsg(_message.Message):
    __slots__ = ("opType", "itemPos", "petId")
    OPTYPE_FIELD_NUMBER: _ClassVar[int]
    ITEMPOS_FIELD_NUMBER: _ClassVar[int]
    PETID_FIELD_NUMBER: _ClassVar[int]
    opType: int
    itemPos: int
    petId: int
    def __init__(self, opType: _Optional[int] = ..., itemPos: _Optional[int] = ..., petId: _Optional[int] = ...) -> None: ...

class LockScreenRspMsg(_message.Message):
    __slots__ = ("screen", "frame")
    SCREEN_FIELD_NUMBER: _ClassVar[int]
    FRAME_FIELD_NUMBER: _ClassVar[int]
    screen: str
    frame: int
    def __init__(self, screen: _Optional[str] = ..., frame: _Optional[int] = ...) -> None: ...

class LoginReqMsg(_message.Message):
    __slots__ = ("playerId", "key", "ekeys")
    PLAYERID_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    EKEYS_FIELD_NUMBER: _ClassVar[int]
    playerId: int
    key: str
    ekeys: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, playerId: _Optional[int] = ..., key: _Optional[str] = ..., ekeys: _Optional[_Iterable[int]] = ...) -> None: ...

class LoginStateMsg(_message.Message):
    __slots__ = ("playerId", "state")
    PLAYERID_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    playerId: int
    state: int
    def __init__(self, playerId: _Optional[int] = ..., state: _Optional[int] = ...) -> None: ...

class LordsBaseInfoMsg(_message.Message):
    __slots__ = ("userId", "serverName", "nickName", "userKeys", "job", "sexJob", "grades", "fashionArm", "fashionWing", "fashionCloth", "fashionHair", "fashionHat", "arm", "isVip", "fightPower", "readyScore", "readyOrder", "readyRewad", "finalScore", "finalOrder", "finalRewad", "readyTurn", "finalTurn", "readyWinCount", "finalWinCount", "isExist", "property1", "property2", "battleResult", "bet_Index", "fightPowerOrder")
    USERID_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    USERKEYS_FIELD_NUMBER: _ClassVar[int]
    JOB_FIELD_NUMBER: _ClassVar[int]
    SEXJOB_FIELD_NUMBER: _ClassVar[int]
    GRADES_FIELD_NUMBER: _ClassVar[int]
    FASHIONARM_FIELD_NUMBER: _ClassVar[int]
    FASHIONWING_FIELD_NUMBER: _ClassVar[int]
    FASHIONCLOTH_FIELD_NUMBER: _ClassVar[int]
    FASHIONHAIR_FIELD_NUMBER: _ClassVar[int]
    FASHIONHAT_FIELD_NUMBER: _ClassVar[int]
    ARM_FIELD_NUMBER: _ClassVar[int]
    ISVIP_FIELD_NUMBER: _ClassVar[int]
    FIGHTPOWER_FIELD_NUMBER: _ClassVar[int]
    READYSCORE_FIELD_NUMBER: _ClassVar[int]
    READYORDER_FIELD_NUMBER: _ClassVar[int]
    READYREWAD_FIELD_NUMBER: _ClassVar[int]
    FINALSCORE_FIELD_NUMBER: _ClassVar[int]
    FINALORDER_FIELD_NUMBER: _ClassVar[int]
    FINALREWAD_FIELD_NUMBER: _ClassVar[int]
    READYTURN_FIELD_NUMBER: _ClassVar[int]
    FINALTURN_FIELD_NUMBER: _ClassVar[int]
    READYWINCOUNT_FIELD_NUMBER: _ClassVar[int]
    FINALWINCOUNT_FIELD_NUMBER: _ClassVar[int]
    ISEXIST_FIELD_NUMBER: _ClassVar[int]
    PROPERTY1_FIELD_NUMBER: _ClassVar[int]
    PROPERTY2_FIELD_NUMBER: _ClassVar[int]
    BATTLERESULT_FIELD_NUMBER: _ClassVar[int]
    BET_INDEX_FIELD_NUMBER: _ClassVar[int]
    FIGHTPOWERORDER_FIELD_NUMBER: _ClassVar[int]
    userId: int
    serverName: str
    nickName: str
    userKeys: str
    job: int
    sexJob: int
    grades: int
    fashionArm: str
    fashionWing: str
    fashionCloth: str
    fashionHair: str
    fashionHat: str
    arm: str
    isVip: bool
    fightPower: int
    readyScore: int
    readyOrder: int
    readyRewad: int
    finalScore: int
    finalOrder: int
    finalRewad: int
    readyTurn: int
    finalTurn: int
    readyWinCount: int
    finalWinCount: int
    isExist: bool
    property1: str
    property2: str
    battleResult: int
    bet_Index: int
    fightPowerOrder: int
    def __init__(self, userId: _Optional[int] = ..., serverName: _Optional[str] = ..., nickName: _Optional[str] = ..., userKeys: _Optional[str] = ..., job: _Optional[int] = ..., sexJob: _Optional[int] = ..., grades: _Optional[int] = ..., fashionArm: _Optional[str] = ..., fashionWing: _Optional[str] = ..., fashionCloth: _Optional[str] = ..., fashionHair: _Optional[str] = ..., fashionHat: _Optional[str] = ..., arm: _Optional[str] = ..., isVip: _Optional[bool] = ..., fightPower: _Optional[int] = ..., readyScore: _Optional[int] = ..., readyOrder: _Optional[int] = ..., readyRewad: _Optional[int] = ..., finalScore: _Optional[int] = ..., finalOrder: _Optional[int] = ..., finalRewad: _Optional[int] = ..., readyTurn: _Optional[int] = ..., finalTurn: _Optional[int] = ..., readyWinCount: _Optional[int] = ..., finalWinCount: _Optional[int] = ..., isExist: _Optional[bool] = ..., property1: _Optional[str] = ..., property2: _Optional[str] = ..., battleResult: _Optional[int] = ..., bet_Index: _Optional[int] = ..., fightPowerOrder: _Optional[int] = ...) -> None: ...

class LordsOrderListMsg(_message.Message):
    __slots__ = ("leftTime", "maxTurn", "currTurn", "myOrder", "winCount", "score", "lordsInfo", "param1", "param2", "param3", "param4")
    LEFTTIME_FIELD_NUMBER: _ClassVar[int]
    MAXTURN_FIELD_NUMBER: _ClassVar[int]
    CURRTURN_FIELD_NUMBER: _ClassVar[int]
    MYORDER_FIELD_NUMBER: _ClassVar[int]
    WINCOUNT_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    LORDSINFO_FIELD_NUMBER: _ClassVar[int]
    PARAM1_FIELD_NUMBER: _ClassVar[int]
    PARAM2_FIELD_NUMBER: _ClassVar[int]
    PARAM3_FIELD_NUMBER: _ClassVar[int]
    PARAM4_FIELD_NUMBER: _ClassVar[int]
    leftTime: int
    maxTurn: int
    currTurn: int
    myOrder: int
    winCount: int
    score: int
    lordsInfo: _containers.RepeatedCompositeFieldContainer[LordsBaseInfoMsg]
    param1: int
    param2: int
    param3: str
    param4: str
    def __init__(self, leftTime: _Optional[int] = ..., maxTurn: _Optional[int] = ..., currTurn: _Optional[int] = ..., myOrder: _Optional[int] = ..., winCount: _Optional[int] = ..., score: _Optional[int] = ..., lordsInfo: _Optional[_Iterable[_Union[LordsBaseInfoMsg, _Mapping]]] = ..., param1: _Optional[int] = ..., param2: _Optional[int] = ..., param3: _Optional[str] = ..., param4: _Optional[str] = ...) -> None: ...

class LotteryMsg(_message.Message):
    __slots__ = ("payedPoint", "totalCount", "leftCount", "dayMaxCount", "onceNeedPoint", "leftMillis", "isOpen", "property1", "property2", "property3", "property4", "dayAddCount")
    PAYEDPOINT_FIELD_NUMBER: _ClassVar[int]
    TOTALCOUNT_FIELD_NUMBER: _ClassVar[int]
    LEFTCOUNT_FIELD_NUMBER: _ClassVar[int]
    DAYMAXCOUNT_FIELD_NUMBER: _ClassVar[int]
    ONCENEEDPOINT_FIELD_NUMBER: _ClassVar[int]
    LEFTMILLIS_FIELD_NUMBER: _ClassVar[int]
    ISOPEN_FIELD_NUMBER: _ClassVar[int]
    PROPERTY1_FIELD_NUMBER: _ClassVar[int]
    PROPERTY2_FIELD_NUMBER: _ClassVar[int]
    PROPERTY3_FIELD_NUMBER: _ClassVar[int]
    PROPERTY4_FIELD_NUMBER: _ClassVar[int]
    DAYADDCOUNT_FIELD_NUMBER: _ClassVar[int]
    payedPoint: int
    totalCount: int
    leftCount: int
    dayMaxCount: int
    onceNeedPoint: int
    leftMillis: int
    isOpen: bool
    property1: str
    property2: str
    property3: _containers.RepeatedScalarFieldContainer[str]
    property4: _containers.RepeatedScalarFieldContainer[str]
    dayAddCount: int
    def __init__(self, payedPoint: _Optional[int] = ..., totalCount: _Optional[int] = ..., leftCount: _Optional[int] = ..., dayMaxCount: _Optional[int] = ..., onceNeedPoint: _Optional[int] = ..., leftMillis: _Optional[int] = ..., isOpen: _Optional[bool] = ..., property1: _Optional[str] = ..., property2: _Optional[str] = ..., property3: _Optional[_Iterable[str]] = ..., property4: _Optional[_Iterable[str]] = ..., dayAddCount: _Optional[int] = ...) -> None: ...

class LuckExchangeInfoListMsg(_message.Message):
    __slots__ = ("luckExchangeInfo",)
    LUCKEXCHANGEINFO_FIELD_NUMBER: _ClassVar[int]
    luckExchangeInfo: _containers.RepeatedCompositeFieldContainer[LuckExchangeInfoMsg]
    def __init__(self, luckExchangeInfo: _Optional[_Iterable[_Union[LuckExchangeInfoMsg, _Mapping]]] = ...) -> None: ...

class LuckExchangeInfoMsg(_message.Message):
    __slots__ = ("exchangeId", "currentLuckValue")
    EXCHANGEID_FIELD_NUMBER: _ClassVar[int]
    CURRENTLUCKVALUE_FIELD_NUMBER: _ClassVar[int]
    exchangeId: str
    currentLuckValue: int
    def __init__(self, exchangeId: _Optional[str] = ..., currentLuckValue: _Optional[int] = ...) -> None: ...

class LuckExchangeItemTempMsg(_message.Message):
    __slots__ = ("itemId", "itemCount", "rare", "dropType")
    ITEMID_FIELD_NUMBER: _ClassVar[int]
    ITEMCOUNT_FIELD_NUMBER: _ClassVar[int]
    RARE_FIELD_NUMBER: _ClassVar[int]
    DROPTYPE_FIELD_NUMBER: _ClassVar[int]
    itemId: int
    itemCount: int
    rare: bool
    dropType: int
    def __init__(self, itemId: _Optional[int] = ..., itemCount: _Optional[int] = ..., rare: _Optional[bool] = ..., dropType: _Optional[int] = ...) -> None: ...

class LuckExchangeOpMsg(_message.Message):
    __slots__ = ("exchangeId", "exchangeCount")
    EXCHANGEID_FIELD_NUMBER: _ClassVar[int]
    EXCHANGECOUNT_FIELD_NUMBER: _ClassVar[int]
    exchangeId: str
    exchangeCount: int
    def __init__(self, exchangeId: _Optional[str] = ..., exchangeCount: _Optional[int] = ...) -> None: ...

class LuckExchangeTempListMsg(_message.Message):
    __slots__ = ("luckExchange",)
    LUCKEXCHANGE_FIELD_NUMBER: _ClassVar[int]
    luckExchange: _containers.RepeatedCompositeFieldContainer[LuckExchangeTempMsg]
    def __init__(self, luckExchange: _Optional[_Iterable[_Union[LuckExchangeTempMsg, _Mapping]]] = ...) -> None: ...

class LuckExchangeTempMsg(_message.Message):
    __slots__ = ("id", "name", "consumeItemId", "consumeItemCount", "luckValue", "startTime", "endTime", "dropItems")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    CONSUMEITEMID_FIELD_NUMBER: _ClassVar[int]
    CONSUMEITEMCOUNT_FIELD_NUMBER: _ClassVar[int]
    LUCKVALUE_FIELD_NUMBER: _ClassVar[int]
    STARTTIME_FIELD_NUMBER: _ClassVar[int]
    ENDTIME_FIELD_NUMBER: _ClassVar[int]
    DROPITEMS_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    consumeItemId: int
    consumeItemCount: int
    luckValue: int
    startTime: str
    endTime: str
    dropItems: _containers.RepeatedCompositeFieldContainer[LuckExchangeItemTempMsg]
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., consumeItemId: _Optional[int] = ..., consumeItemCount: _Optional[int] = ..., luckValue: _Optional[int] = ..., startTime: _Optional[str] = ..., endTime: _Optional[str] = ..., dropItems: _Optional[_Iterable[_Union[LuckExchangeItemTempMsg, _Mapping]]] = ...) -> None: ...

class MailCheckMsg(_message.Message):
    __slots__ = ("op", "state", "pin", "mail")
    OP_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    PIN_FIELD_NUMBER: _ClassVar[int]
    MAIL_FIELD_NUMBER: _ClassVar[int]
    op: int
    state: int
    pin: int
    mail: str
    def __init__(self, op: _Optional[int] = ..., state: _Optional[int] = ..., pin: _Optional[int] = ..., mail: _Optional[str] = ...) -> None: ...

class MailDelReqMsg(_message.Message):
    __slots__ = ("delList",)
    DELLIST_FIELD_NUMBER: _ClassVar[int]
    delList: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, delList: _Optional[_Iterable[int]] = ...) -> None: ...

class MailInfoMsg(_message.Message):
    __slots__ = ("id", "mailType", "sendId", "sendNickName", "receiveId", "receiveNickName", "sendDate", "readDate", "title", "contents", "removeDate", "validityDate", "annex1", "annex1Name", "annex1Count", "isAnnex1", "annex2", "annex2Name", "annex2Count", "isAnnex2", "annex3", "annex3Name", "annex3Count", "isAnnex3", "annex4", "annex4Name", "annex4Count", "isAnnex4", "annex5", "annex5Name", "annex5Count", "isAnnex5", "isExist", "sendType", "sendPlayerGrades")
    ID_FIELD_NUMBER: _ClassVar[int]
    MAILTYPE_FIELD_NUMBER: _ClassVar[int]
    SENDID_FIELD_NUMBER: _ClassVar[int]
    SENDNICKNAME_FIELD_NUMBER: _ClassVar[int]
    RECEIVEID_FIELD_NUMBER: _ClassVar[int]
    RECEIVENICKNAME_FIELD_NUMBER: _ClassVar[int]
    SENDDATE_FIELD_NUMBER: _ClassVar[int]
    READDATE_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    CONTENTS_FIELD_NUMBER: _ClassVar[int]
    REMOVEDATE_FIELD_NUMBER: _ClassVar[int]
    VALIDITYDATE_FIELD_NUMBER: _ClassVar[int]
    ANNEX1_FIELD_NUMBER: _ClassVar[int]
    ANNEX1NAME_FIELD_NUMBER: _ClassVar[int]
    ANNEX1COUNT_FIELD_NUMBER: _ClassVar[int]
    ISANNEX1_FIELD_NUMBER: _ClassVar[int]
    ANNEX2_FIELD_NUMBER: _ClassVar[int]
    ANNEX2NAME_FIELD_NUMBER: _ClassVar[int]
    ANNEX2COUNT_FIELD_NUMBER: _ClassVar[int]
    ISANNEX2_FIELD_NUMBER: _ClassVar[int]
    ANNEX3_FIELD_NUMBER: _ClassVar[int]
    ANNEX3NAME_FIELD_NUMBER: _ClassVar[int]
    ANNEX3COUNT_FIELD_NUMBER: _ClassVar[int]
    ISANNEX3_FIELD_NUMBER: _ClassVar[int]
    ANNEX4_FIELD_NUMBER: _ClassVar[int]
    ANNEX4NAME_FIELD_NUMBER: _ClassVar[int]
    ANNEX4COUNT_FIELD_NUMBER: _ClassVar[int]
    ISANNEX4_FIELD_NUMBER: _ClassVar[int]
    ANNEX5_FIELD_NUMBER: _ClassVar[int]
    ANNEX5NAME_FIELD_NUMBER: _ClassVar[int]
    ANNEX5COUNT_FIELD_NUMBER: _ClassVar[int]
    ISANNEX5_FIELD_NUMBER: _ClassVar[int]
    ISEXIST_FIELD_NUMBER: _ClassVar[int]
    SENDTYPE_FIELD_NUMBER: _ClassVar[int]
    SENDPLAYERGRADES_FIELD_NUMBER: _ClassVar[int]
    id: int
    mailType: int
    sendId: int
    sendNickName: str
    receiveId: int
    receiveNickName: str
    sendDate: str
    readDate: str
    title: str
    contents: str
    removeDate: str
    validityDate: int
    annex1: int
    annex1Name: int
    annex1Count: int
    isAnnex1: bool
    annex2: int
    annex2Name: int
    annex2Count: int
    isAnnex2: bool
    annex3: int
    annex3Name: int
    annex3Count: int
    isAnnex3: bool
    annex4: int
    annex4Name: int
    annex4Count: int
    isAnnex4: bool
    annex5: int
    annex5Name: int
    annex5Count: int
    isAnnex5: bool
    isExist: bool
    sendType: int
    sendPlayerGrades: int
    def __init__(self, id: _Optional[int] = ..., mailType: _Optional[int] = ..., sendId: _Optional[int] = ..., sendNickName: _Optional[str] = ..., receiveId: _Optional[int] = ..., receiveNickName: _Optional[str] = ..., sendDate: _Optional[str] = ..., readDate: _Optional[str] = ..., title: _Optional[str] = ..., contents: _Optional[str] = ..., removeDate: _Optional[str] = ..., validityDate: _Optional[int] = ..., annex1: _Optional[int] = ..., annex1Name: _Optional[int] = ..., annex1Count: _Optional[int] = ..., isAnnex1: _Optional[bool] = ..., annex2: _Optional[int] = ..., annex2Name: _Optional[int] = ..., annex2Count: _Optional[int] = ..., isAnnex2: _Optional[bool] = ..., annex3: _Optional[int] = ..., annex3Name: _Optional[int] = ..., annex3Count: _Optional[int] = ..., isAnnex3: _Optional[bool] = ..., annex4: _Optional[int] = ..., annex4Name: _Optional[int] = ..., annex4Count: _Optional[int] = ..., isAnnex4: _Optional[bool] = ..., annex5: _Optional[int] = ..., annex5Name: _Optional[int] = ..., annex5Count: _Optional[int] = ..., isAnnex5: _Optional[bool] = ..., isExist: _Optional[bool] = ..., sendType: _Optional[int] = ..., sendPlayerGrades: _Optional[int] = ...) -> None: ...

class MailListReqMsg(_message.Message):
    __slots__ = ("mailId", "reqType")
    MAILID_FIELD_NUMBER: _ClassVar[int]
    REQTYPE_FIELD_NUMBER: _ClassVar[int]
    mailId: int
    reqType: int
    def __init__(self, mailId: _Optional[int] = ..., reqType: _Optional[int] = ...) -> None: ...

class MailMsg(_message.Message):
    __slots__ = ("playerId", "mailId", "position", "mailsIdArray")
    PLAYERID_FIELD_NUMBER: _ClassVar[int]
    MAILID_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    MAILSIDARRAY_FIELD_NUMBER: _ClassVar[int]
    playerId: int
    mailId: int
    position: _containers.RepeatedScalarFieldContainer[int]
    mailsIdArray: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, playerId: _Optional[int] = ..., mailId: _Optional[int] = ..., position: _Optional[_Iterable[int]] = ..., mailsIdArray: _Optional[_Iterable[int]] = ...) -> None: ...

class MailPickupRspMsg(_message.Message):
    __slots__ = ("pickupResult",)
    PICKUPRESULT_FIELD_NUMBER: _ClassVar[int]
    pickupResult: _containers.RepeatedCompositeFieldContainer[PickupResult]
    def __init__(self, pickupResult: _Optional[_Iterable[_Union[PickupResult, _Mapping]]] = ...) -> None: ...

class MailSendReqMsg(_message.Message):
    __slots__ = ("receiverUserId", "title", "contents", "sendType", "payType")
    RECEIVERUSERID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    CONTENTS_FIELD_NUMBER: _ClassVar[int]
    SENDTYPE_FIELD_NUMBER: _ClassVar[int]
    PAYTYPE_FIELD_NUMBER: _ClassVar[int]
    receiverUserId: _containers.RepeatedScalarFieldContainer[int]
    title: str
    contents: str
    sendType: int
    payType: int
    def __init__(self, receiverUserId: _Optional[_Iterable[int]] = ..., title: _Optional[str] = ..., contents: _Optional[str] = ..., sendType: _Optional[int] = ..., payType: _Optional[int] = ...) -> None: ...

class MainDiscountInfo(_message.Message):
    __slots__ = ("id", "site", "shopId", "templateId", "counts", "shopId1", "templateId1", "count1", "shopId2", "templateId2", "count2", "shopId3", "templateId3", "count3", "shopId4", "templateId4", "count4", "shopId5", "templateId5", "count5", "shopId6", "templateId6", "count6", "shopId7", "templateId7", "count7", "shopId8", "templateId8", "count8", "sortId", "discount", "beginDate", "endDate", "oneDayCount", "maxCount", "currentCount", "maxCurrentDate", "isGift", "url", "names", "price", "type", "limitCount", "vip", "level1", "price1", "level2", "price2", "level3", "price3", "sendDate", "refreshInterval", "frontMoney")
    ID_FIELD_NUMBER: _ClassVar[int]
    SITE_FIELD_NUMBER: _ClassVar[int]
    SHOPID_FIELD_NUMBER: _ClassVar[int]
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    COUNTS_FIELD_NUMBER: _ClassVar[int]
    SHOPID1_FIELD_NUMBER: _ClassVar[int]
    TEMPLATEID1_FIELD_NUMBER: _ClassVar[int]
    COUNT1_FIELD_NUMBER: _ClassVar[int]
    SHOPID2_FIELD_NUMBER: _ClassVar[int]
    TEMPLATEID2_FIELD_NUMBER: _ClassVar[int]
    COUNT2_FIELD_NUMBER: _ClassVar[int]
    SHOPID3_FIELD_NUMBER: _ClassVar[int]
    TEMPLATEID3_FIELD_NUMBER: _ClassVar[int]
    COUNT3_FIELD_NUMBER: _ClassVar[int]
    SHOPID4_FIELD_NUMBER: _ClassVar[int]
    TEMPLATEID4_FIELD_NUMBER: _ClassVar[int]
    COUNT4_FIELD_NUMBER: _ClassVar[int]
    SHOPID5_FIELD_NUMBER: _ClassVar[int]
    TEMPLATEID5_FIELD_NUMBER: _ClassVar[int]
    COUNT5_FIELD_NUMBER: _ClassVar[int]
    SHOPID6_FIELD_NUMBER: _ClassVar[int]
    TEMPLATEID6_FIELD_NUMBER: _ClassVar[int]
    COUNT6_FIELD_NUMBER: _ClassVar[int]
    SHOPID7_FIELD_NUMBER: _ClassVar[int]
    TEMPLATEID7_FIELD_NUMBER: _ClassVar[int]
    COUNT7_FIELD_NUMBER: _ClassVar[int]
    SHOPID8_FIELD_NUMBER: _ClassVar[int]
    TEMPLATEID8_FIELD_NUMBER: _ClassVar[int]
    COUNT8_FIELD_NUMBER: _ClassVar[int]
    SORTID_FIELD_NUMBER: _ClassVar[int]
    DISCOUNT_FIELD_NUMBER: _ClassVar[int]
    BEGINDATE_FIELD_NUMBER: _ClassVar[int]
    ENDDATE_FIELD_NUMBER: _ClassVar[int]
    ONEDAYCOUNT_FIELD_NUMBER: _ClassVar[int]
    MAXCOUNT_FIELD_NUMBER: _ClassVar[int]
    CURRENTCOUNT_FIELD_NUMBER: _ClassVar[int]
    MAXCURRENTDATE_FIELD_NUMBER: _ClassVar[int]
    ISGIFT_FIELD_NUMBER: _ClassVar[int]
    URL_FIELD_NUMBER: _ClassVar[int]
    NAMES_FIELD_NUMBER: _ClassVar[int]
    PRICE_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    LIMITCOUNT_FIELD_NUMBER: _ClassVar[int]
    VIP_FIELD_NUMBER: _ClassVar[int]
    LEVEL1_FIELD_NUMBER: _ClassVar[int]
    PRICE1_FIELD_NUMBER: _ClassVar[int]
    LEVEL2_FIELD_NUMBER: _ClassVar[int]
    PRICE2_FIELD_NUMBER: _ClassVar[int]
    LEVEL3_FIELD_NUMBER: _ClassVar[int]
    PRICE3_FIELD_NUMBER: _ClassVar[int]
    SENDDATE_FIELD_NUMBER: _ClassVar[int]
    REFRESHINTERVAL_FIELD_NUMBER: _ClassVar[int]
    FRONTMONEY_FIELD_NUMBER: _ClassVar[int]
    id: int
    site: int
    shopId: int
    templateId: int
    counts: int
    shopId1: int
    templateId1: int
    count1: int
    shopId2: int
    templateId2: int
    count2: int
    shopId3: int
    templateId3: int
    count3: int
    shopId4: int
    templateId4: int
    count4: int
    shopId5: int
    templateId5: int
    count5: int
    shopId6: int
    templateId6: int
    count6: int
    shopId7: int
    templateId7: int
    count7: int
    shopId8: int
    templateId8: int
    count8: int
    sortId: int
    discount: int
    beginDate: str
    endDate: str
    oneDayCount: int
    maxCount: int
    currentCount: int
    maxCurrentDate: str
    isGift: bool
    url: str
    names: str
    price: int
    type: int
    limitCount: int
    vip: int
    level1: int
    price1: int
    level2: int
    price2: int
    level3: int
    price3: int
    sendDate: str
    refreshInterval: int
    frontMoney: int
    def __init__(self, id: _Optional[int] = ..., site: _Optional[int] = ..., shopId: _Optional[int] = ..., templateId: _Optional[int] = ..., counts: _Optional[int] = ..., shopId1: _Optional[int] = ..., templateId1: _Optional[int] = ..., count1: _Optional[int] = ..., shopId2: _Optional[int] = ..., templateId2: _Optional[int] = ..., count2: _Optional[int] = ..., shopId3: _Optional[int] = ..., templateId3: _Optional[int] = ..., count3: _Optional[int] = ..., shopId4: _Optional[int] = ..., templateId4: _Optional[int] = ..., count4: _Optional[int] = ..., shopId5: _Optional[int] = ..., templateId5: _Optional[int] = ..., count5: _Optional[int] = ..., shopId6: _Optional[int] = ..., templateId6: _Optional[int] = ..., count6: _Optional[int] = ..., shopId7: _Optional[int] = ..., templateId7: _Optional[int] = ..., count7: _Optional[int] = ..., shopId8: _Optional[int] = ..., templateId8: _Optional[int] = ..., count8: _Optional[int] = ..., sortId: _Optional[int] = ..., discount: _Optional[int] = ..., beginDate: _Optional[str] = ..., endDate: _Optional[str] = ..., oneDayCount: _Optional[int] = ..., maxCount: _Optional[int] = ..., currentCount: _Optional[int] = ..., maxCurrentDate: _Optional[str] = ..., isGift: _Optional[bool] = ..., url: _Optional[str] = ..., names: _Optional[str] = ..., price: _Optional[int] = ..., type: _Optional[int] = ..., limitCount: _Optional[int] = ..., vip: _Optional[int] = ..., level1: _Optional[int] = ..., price1: _Optional[int] = ..., level2: _Optional[int] = ..., price2: _Optional[int] = ..., level3: _Optional[int] = ..., price3: _Optional[int] = ..., sendDate: _Optional[str] = ..., refreshInterval: _Optional[int] = ..., frontMoney: _Optional[int] = ...) -> None: ...

class MainGoodInfo(_message.Message):
    __slots__ = ("id", "shopId", "templateId", "sortId", "types")
    ID_FIELD_NUMBER: _ClassVar[int]
    SHOPID_FIELD_NUMBER: _ClassVar[int]
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    SORTID_FIELD_NUMBER: _ClassVar[int]
    TYPES_FIELD_NUMBER: _ClassVar[int]
    id: int
    shopId: int
    templateId: int
    sortId: int
    types: int
    def __init__(self, id: _Optional[int] = ..., shopId: _Optional[int] = ..., templateId: _Optional[int] = ..., sortId: _Optional[int] = ..., types: _Optional[int] = ...) -> None: ...

class MainUrlInfo(_message.Message):
    __slots__ = ("id", "url", "site")
    ID_FIELD_NUMBER: _ClassVar[int]
    URL_FIELD_NUMBER: _ClassVar[int]
    SITE_FIELD_NUMBER: _ClassVar[int]
    id: int
    url: str
    site: int
    def __init__(self, id: _Optional[int] = ..., url: _Optional[str] = ..., site: _Optional[int] = ...) -> None: ...

class MallItemBuyMsg(_message.Message):
    __slots__ = ("id", "userId", "mallItem", "bidupPoint", "buyTime")
    ID_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    MALLITEM_FIELD_NUMBER: _ClassVar[int]
    BIDUPPOINT_FIELD_NUMBER: _ClassVar[int]
    BUYTIME_FIELD_NUMBER: _ClassVar[int]
    id: int
    userId: int
    mallItem: MallItemMsg
    bidupPoint: int
    buyTime: str
    def __init__(self, id: _Optional[int] = ..., userId: _Optional[int] = ..., mallItem: _Optional[_Union[MallItemMsg, _Mapping]] = ..., bidupPoint: _Optional[int] = ..., buyTime: _Optional[str] = ...) -> None: ...

class MallItemMsg(_message.Message):
    __slots__ = ("id", "templateId", "userId", "nickName", "point", "fixPoint", "hour", "itemFrom", "startTime", "maxAuctionId", "itemInfo")
    ID_FIELD_NUMBER: _ClassVar[int]
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    POINT_FIELD_NUMBER: _ClassVar[int]
    FIXPOINT_FIELD_NUMBER: _ClassVar[int]
    HOUR_FIELD_NUMBER: _ClassVar[int]
    ITEMFROM_FIELD_NUMBER: _ClassVar[int]
    STARTTIME_FIELD_NUMBER: _ClassVar[int]
    MAXAUCTIONID_FIELD_NUMBER: _ClassVar[int]
    ITEMINFO_FIELD_NUMBER: _ClassVar[int]
    id: int
    templateId: int
    userId: int
    nickName: str
    point: int
    fixPoint: int
    hour: int
    itemFrom: int
    startTime: str
    maxAuctionId: int
    itemInfo: SimpleItemInfoMsg
    def __init__(self, id: _Optional[int] = ..., templateId: _Optional[int] = ..., userId: _Optional[int] = ..., nickName: _Optional[str] = ..., point: _Optional[int] = ..., fixPoint: _Optional[int] = ..., hour: _Optional[int] = ..., itemFrom: _Optional[int] = ..., startTime: _Optional[str] = ..., maxAuctionId: _Optional[int] = ..., itemInfo: _Optional[_Union[SimpleItemInfoMsg, _Mapping]] = ...) -> None: ...

class MallItemViewReqMsg(_message.Message):
    __slots__ = ("page", "count", "orderBy", "orderType")
    PAGE_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    FROM_FIELD_NUMBER: _ClassVar[int]
    ORDERBY_FIELD_NUMBER: _ClassVar[int]
    ORDERTYPE_FIELD_NUMBER: _ClassVar[int]
    page: int
    count: int
    orderBy: int
    orderType: int
    def __init__(self, page: _Optional[int] = ..., count: _Optional[int] = ..., orderBy: _Optional[int] = ..., orderType: _Optional[int] = ..., **kwargs) -> None: ...

class MapBossMsg(_message.Message):
    __slots__ = ("count1", "count2", "count3", "bosslist", "leftBossTime", "leftFogTime")
    COUNT1_FIELD_NUMBER: _ClassVar[int]
    COUNT2_FIELD_NUMBER: _ClassVar[int]
    COUNT3_FIELD_NUMBER: _ClassVar[int]
    BOSSLIST_FIELD_NUMBER: _ClassVar[int]
    LEFTBOSSTIME_FIELD_NUMBER: _ClassVar[int]
    LEFTFOGTIME_FIELD_NUMBER: _ClassVar[int]
    count1: int
    count2: int
    count3: int
    bosslist: _containers.RepeatedCompositeFieldContainer[BossMsg]
    leftBossTime: int
    leftFogTime: int
    def __init__(self, count1: _Optional[int] = ..., count2: _Optional[int] = ..., count3: _Optional[int] = ..., bosslist: _Optional[_Iterable[_Union[BossMsg, _Mapping]]] = ..., leftBossTime: _Optional[int] = ..., leftFogTime: _Optional[int] = ...) -> None: ...

class MapBossQuestMsg(_message.Message):
    __slots__ = ("mapId",)
    MAPID_FIELD_NUMBER: _ClassVar[int]
    mapId: int
    def __init__(self, mapId: _Optional[int] = ...) -> None: ...

class MapBoxMsg(_message.Message):
    __slots__ = ("boxlist",)
    BOXLIST_FIELD_NUMBER: _ClassVar[int]
    boxlist: _containers.RepeatedCompositeFieldContainer[ArmyBoxMsg]
    def __init__(self, boxlist: _Optional[_Iterable[_Union[ArmyBoxMsg, _Mapping]]] = ...) -> None: ...

class MapPhysicAttackMsg(_message.Message):
    __slots__ = ("mapId", "posX", "posY")
    MAPID_FIELD_NUMBER: _ClassVar[int]
    POSX_FIELD_NUMBER: _ClassVar[int]
    POSY_FIELD_NUMBER: _ClassVar[int]
    mapId: int
    posX: int
    posY: int
    def __init__(self, mapId: _Optional[int] = ..., posX: _Optional[int] = ..., posY: _Optional[int] = ...) -> None: ...

class MapUpdatedMsg(_message.Message):
    __slots__ = ("updatedType", "army", "wildLand", "baseCastle")
    UPDATEDTYPE_FIELD_NUMBER: _ClassVar[int]
    ARMY_FIELD_NUMBER: _ClassVar[int]
    WILDLAND_FIELD_NUMBER: _ClassVar[int]
    BASECASTLE_FIELD_NUMBER: _ClassVar[int]
    updatedType: int
    army: ArmyArmyMsg
    wildLand: WildLandMsg
    baseCastle: BaseCastleMsg
    def __init__(self, updatedType: _Optional[int] = ..., army: _Optional[_Union[ArmyArmyMsg, _Mapping]] = ..., wildLand: _Optional[_Union[WildLandMsg, _Mapping]] = ..., baseCastle: _Optional[_Union[BaseCastleMsg, _Mapping]] = ...) -> None: ...

class MarriageDataMsg(_message.Message):
    __slots__ = ("userId", "type", "marriageState", "happy", "mateHappy", "ring", "godTree")
    USERID_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    MARRIAGESTATE_FIELD_NUMBER: _ClassVar[int]
    HAPPY_FIELD_NUMBER: _ClassVar[int]
    MATEHAPPY_FIELD_NUMBER: _ClassVar[int]
    RING_FIELD_NUMBER: _ClassVar[int]
    GODTREE_FIELD_NUMBER: _ClassVar[int]
    userId: int
    type: int
    marriageState: int
    happy: MarriageHappyMsg
    mateHappy: MarriageHappyMsg
    ring: MarriageRingMsg
    godTree: MarriageGodTreeMsg
    def __init__(self, userId: _Optional[int] = ..., type: _Optional[int] = ..., marriageState: _Optional[int] = ..., happy: _Optional[_Union[MarriageHappyMsg, _Mapping]] = ..., mateHappy: _Optional[_Union[MarriageHappyMsg, _Mapping]] = ..., ring: _Optional[_Union[MarriageRingMsg, _Mapping]] = ..., godTree: _Optional[_Union[MarriageGodTreeMsg, _Mapping]] = ...) -> None: ...

class MarriageGodTreeMsg(_message.Message):
    __slots__ = ("treeGp", "treeGrade", "treeGoldWater", "treeDiamondWater", "treeState", "treeStateValue", "treeEarningDate", "treeMateState")
    TREEGP_FIELD_NUMBER: _ClassVar[int]
    TREEGRADE_FIELD_NUMBER: _ClassVar[int]
    TREEGOLDWATER_FIELD_NUMBER: _ClassVar[int]
    TREEDIAMONDWATER_FIELD_NUMBER: _ClassVar[int]
    TREESTATE_FIELD_NUMBER: _ClassVar[int]
    TREESTATEVALUE_FIELD_NUMBER: _ClassVar[int]
    TREEEARNINGDATE_FIELD_NUMBER: _ClassVar[int]
    TREEMATESTATE_FIELD_NUMBER: _ClassVar[int]
    treeGp: int
    treeGrade: int
    treeGoldWater: int
    treeDiamondWater: int
    treeState: int
    treeStateValue: int
    treeEarningDate: str
    treeMateState: int
    def __init__(self, treeGp: _Optional[int] = ..., treeGrade: _Optional[int] = ..., treeGoldWater: _Optional[int] = ..., treeDiamondWater: _Optional[int] = ..., treeState: _Optional[int] = ..., treeStateValue: _Optional[int] = ..., treeEarningDate: _Optional[str] = ..., treeMateState: _Optional[int] = ...) -> None: ...

class MarriageHappyMsg(_message.Message):
    __slots__ = ("happyGp", "happyGrade", "happyHelp")
    HAPPYGP_FIELD_NUMBER: _ClassVar[int]
    HAPPYGRADE_FIELD_NUMBER: _ClassVar[int]
    HAPPYHELP_FIELD_NUMBER: _ClassVar[int]
    happyGp: int
    happyGrade: int
    happyHelp: int
    def __init__(self, happyGp: _Optional[int] = ..., happyGrade: _Optional[int] = ..., happyHelp: _Optional[int] = ...) -> None: ...

class MarriageHeartMsg(_message.Message):
    __slots__ = ("curQuestion", "lastQuestions", "syncRate", "maxOrder")
    CURQUESTION_FIELD_NUMBER: _ClassVar[int]
    LASTQUESTIONS_FIELD_NUMBER: _ClassVar[int]
    SYNCRATE_FIELD_NUMBER: _ClassVar[int]
    MAXORDER_FIELD_NUMBER: _ClassVar[int]
    curQuestion: HeartMsg
    lastQuestions: _containers.RepeatedCompositeFieldContainer[HeartMsg]
    syncRate: int
    maxOrder: int
    def __init__(self, curQuestion: _Optional[_Union[HeartMsg, _Mapping]] = ..., lastQuestions: _Optional[_Iterable[_Union[HeartMsg, _Mapping]]] = ..., syncRate: _Optional[int] = ..., maxOrder: _Optional[int] = ...) -> None: ...

class MarriageMsg(_message.Message):
    __slots__ = ("userId", "state", "happy", "templateId", "engageTime", "speTemplateId", "marTime", "questCount", "ringGrade", "nickName", "ringGp", "overTime", "answerNum", "ringGrade1", "logoutDays")
    USERID_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    HAPPY_FIELD_NUMBER: _ClassVar[int]
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    ENGAGETIME_FIELD_NUMBER: _ClassVar[int]
    SPETEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    MARTIME_FIELD_NUMBER: _ClassVar[int]
    QUESTCOUNT_FIELD_NUMBER: _ClassVar[int]
    RINGGRADE_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    RINGGP_FIELD_NUMBER: _ClassVar[int]
    OVERTIME_FIELD_NUMBER: _ClassVar[int]
    ANSWERNUM_FIELD_NUMBER: _ClassVar[int]
    RINGGRADE1_FIELD_NUMBER: _ClassVar[int]
    LOGOUTDAYS_FIELD_NUMBER: _ClassVar[int]
    userId: int
    state: int
    happy: int
    templateId: int
    engageTime: str
    speTemplateId: int
    marTime: str
    questCount: int
    ringGrade: int
    nickName: str
    ringGp: int
    overTime: int
    answerNum: int
    ringGrade1: int
    logoutDays: int
    def __init__(self, userId: _Optional[int] = ..., state: _Optional[int] = ..., happy: _Optional[int] = ..., templateId: _Optional[int] = ..., engageTime: _Optional[str] = ..., speTemplateId: _Optional[int] = ..., marTime: _Optional[str] = ..., questCount: _Optional[int] = ..., ringGrade: _Optional[int] = ..., nickName: _Optional[str] = ..., ringGp: _Optional[int] = ..., overTime: _Optional[int] = ..., answerNum: _Optional[int] = ..., ringGrade1: _Optional[int] = ..., logoutDays: _Optional[int] = ...) -> None: ...

class MarriageOpMsg(_message.Message):
    __slots__ = ("userId", "opType", "payType", "property1", "property2", "property3", "property4", "property5", "userIds", "properties", "isNoGet")
    USERID_FIELD_NUMBER: _ClassVar[int]
    OPTYPE_FIELD_NUMBER: _ClassVar[int]
    PAYTYPE_FIELD_NUMBER: _ClassVar[int]
    PROPERTY1_FIELD_NUMBER: _ClassVar[int]
    PROPERTY2_FIELD_NUMBER: _ClassVar[int]
    PROPERTY3_FIELD_NUMBER: _ClassVar[int]
    PROPERTY4_FIELD_NUMBER: _ClassVar[int]
    PROPERTY5_FIELD_NUMBER: _ClassVar[int]
    USERIDS_FIELD_NUMBER: _ClassVar[int]
    PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    ISNOGET_FIELD_NUMBER: _ClassVar[int]
    userId: int
    opType: int
    payType: int
    property1: int
    property2: int
    property3: str
    property4: str
    property5: bool
    userIds: _containers.RepeatedScalarFieldContainer[int]
    properties: _containers.RepeatedCompositeFieldContainer[MarriagePropertyListMsg]
    isNoGet: bool
    def __init__(self, userId: _Optional[int] = ..., opType: _Optional[int] = ..., payType: _Optional[int] = ..., property1: _Optional[int] = ..., property2: _Optional[int] = ..., property3: _Optional[str] = ..., property4: _Optional[str] = ..., property5: _Optional[bool] = ..., userIds: _Optional[_Iterable[int]] = ..., properties: _Optional[_Iterable[_Union[MarriagePropertyListMsg, _Mapping]]] = ..., isNoGet: _Optional[bool] = ...) -> None: ...

class MarriageProMsg(_message.Message):
    __slots__ = ("userIdA", "nickNameA", "jobA", "userIdB", "nickNameB", "jobB", "property1", "property2", "property3", "property4", "property5", "property6", "property7", "property8", "property9", "property10")
    USERIDA_FIELD_NUMBER: _ClassVar[int]
    NICKNAMEA_FIELD_NUMBER: _ClassVar[int]
    JOBA_FIELD_NUMBER: _ClassVar[int]
    USERIDB_FIELD_NUMBER: _ClassVar[int]
    NICKNAMEB_FIELD_NUMBER: _ClassVar[int]
    JOBB_FIELD_NUMBER: _ClassVar[int]
    PROPERTY1_FIELD_NUMBER: _ClassVar[int]
    PROPERTY2_FIELD_NUMBER: _ClassVar[int]
    PROPERTY3_FIELD_NUMBER: _ClassVar[int]
    PROPERTY4_FIELD_NUMBER: _ClassVar[int]
    PROPERTY5_FIELD_NUMBER: _ClassVar[int]
    PROPERTY6_FIELD_NUMBER: _ClassVar[int]
    PROPERTY7_FIELD_NUMBER: _ClassVar[int]
    PROPERTY8_FIELD_NUMBER: _ClassVar[int]
    PROPERTY9_FIELD_NUMBER: _ClassVar[int]
    PROPERTY10_FIELD_NUMBER: _ClassVar[int]
    userIdA: int
    nickNameA: str
    jobA: int
    userIdB: int
    nickNameB: str
    jobB: int
    property1: bool
    property2: int
    property3: int
    property4: str
    property5: str
    property6: int
    property7: int
    property8: int
    property9: int
    property10: int
    def __init__(self, userIdA: _Optional[int] = ..., nickNameA: _Optional[str] = ..., jobA: _Optional[int] = ..., userIdB: _Optional[int] = ..., nickNameB: _Optional[str] = ..., jobB: _Optional[int] = ..., property1: _Optional[bool] = ..., property2: _Optional[int] = ..., property3: _Optional[int] = ..., property4: _Optional[str] = ..., property5: _Optional[str] = ..., property6: _Optional[int] = ..., property7: _Optional[int] = ..., property8: _Optional[int] = ..., property9: _Optional[int] = ..., property10: _Optional[int] = ...) -> None: ...

class MarriagePropertyListMsg(_message.Message):
    __slots__ = ("property1", "property2")
    PROPERTY1_FIELD_NUMBER: _ClassVar[int]
    PROPERTY2_FIELD_NUMBER: _ClassVar[int]
    property1: int
    property2: int
    def __init__(self, property1: _Optional[int] = ..., property2: _Optional[int] = ...) -> None: ...

class MarriageRingMsg(_message.Message):
    __slots__ = ("ringGp", "ringGrade", "ringSkill")
    RINGGP_FIELD_NUMBER: _ClassVar[int]
    RINGGRADE_FIELD_NUMBER: _ClassVar[int]
    RINGSKILL_FIELD_NUMBER: _ClassVar[int]
    ringGp: int
    ringGrade: int
    ringSkill: str
    def __init__(self, ringGp: _Optional[int] = ..., ringGrade: _Optional[int] = ..., ringSkill: _Optional[str] = ...) -> None: ...

class MarriageTreeMsg(_message.Message):
    __slots__ = ("userIdA", "nickNameA", "jobA", "userIdB", "nickNameB", "jobB", "stateValue", "feedCount", "startTime", "endTime", "trainACount", "trainBCount", "trainAType", "trainBType", "isGetA", "isGetB", "treeState", "feedUser")
    USERIDA_FIELD_NUMBER: _ClassVar[int]
    NICKNAMEA_FIELD_NUMBER: _ClassVar[int]
    JOBA_FIELD_NUMBER: _ClassVar[int]
    USERIDB_FIELD_NUMBER: _ClassVar[int]
    NICKNAMEB_FIELD_NUMBER: _ClassVar[int]
    JOBB_FIELD_NUMBER: _ClassVar[int]
    STATEVALUE_FIELD_NUMBER: _ClassVar[int]
    FEEDCOUNT_FIELD_NUMBER: _ClassVar[int]
    STARTTIME_FIELD_NUMBER: _ClassVar[int]
    ENDTIME_FIELD_NUMBER: _ClassVar[int]
    TRAINACOUNT_FIELD_NUMBER: _ClassVar[int]
    TRAINBCOUNT_FIELD_NUMBER: _ClassVar[int]
    TRAINATYPE_FIELD_NUMBER: _ClassVar[int]
    TRAINBTYPE_FIELD_NUMBER: _ClassVar[int]
    ISGETA_FIELD_NUMBER: _ClassVar[int]
    ISGETB_FIELD_NUMBER: _ClassVar[int]
    TREESTATE_FIELD_NUMBER: _ClassVar[int]
    FEEDUSER_FIELD_NUMBER: _ClassVar[int]
    userIdA: int
    nickNameA: str
    jobA: int
    userIdB: int
    nickNameB: str
    jobB: int
    stateValue: int
    feedCount: int
    startTime: str
    endTime: str
    trainACount: int
    trainBCount: int
    trainAType: int
    trainBType: int
    isGetA: bool
    isGetB: bool
    treeState: str
    feedUser: int
    def __init__(self, userIdA: _Optional[int] = ..., nickNameA: _Optional[str] = ..., jobA: _Optional[int] = ..., userIdB: _Optional[int] = ..., nickNameB: _Optional[str] = ..., jobB: _Optional[int] = ..., stateValue: _Optional[int] = ..., feedCount: _Optional[int] = ..., startTime: _Optional[str] = ..., endTime: _Optional[str] = ..., trainACount: _Optional[int] = ..., trainBCount: _Optional[int] = ..., trainAType: _Optional[int] = ..., trainBType: _Optional[int] = ..., isGetA: _Optional[bool] = ..., isGetB: _Optional[bool] = ..., treeState: _Optional[str] = ..., feedUser: _Optional[int] = ...) -> None: ...

class MatchStateMsg(_message.Message):
    __slots__ = ("matchState", "param1", "param2")
    MATCHSTATE_FIELD_NUMBER: _ClassVar[int]
    PARAM1_FIELD_NUMBER: _ClassVar[int]
    PARAM2_FIELD_NUMBER: _ClassVar[int]
    matchState: bool
    param1: str
    param2: str
    def __init__(self, matchState: _Optional[bool] = ..., param1: _Optional[str] = ..., param2: _Optional[str] = ...) -> None: ...

class MateLordsInfoMsg(_message.Message):
    __slots__ = ("uuid", "teamUid", "userId", "serverName", "nickName", "userKeys", "job", "sexJob", "grades", "fightPower", "totalWinCount", "teamType", "warIndex", "curreOrder", "result", "turnCount", "addScore", "totalScore", "property1", "clearRateItems", "descScore")
    UUID_FIELD_NUMBER: _ClassVar[int]
    TEAMUID_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    USERKEYS_FIELD_NUMBER: _ClassVar[int]
    JOB_FIELD_NUMBER: _ClassVar[int]
    SEXJOB_FIELD_NUMBER: _ClassVar[int]
    GRADES_FIELD_NUMBER: _ClassVar[int]
    FIGHTPOWER_FIELD_NUMBER: _ClassVar[int]
    TOTALWINCOUNT_FIELD_NUMBER: _ClassVar[int]
    TEAMTYPE_FIELD_NUMBER: _ClassVar[int]
    WARINDEX_FIELD_NUMBER: _ClassVar[int]
    CURREORDER_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    TURNCOUNT_FIELD_NUMBER: _ClassVar[int]
    ADDSCORE_FIELD_NUMBER: _ClassVar[int]
    TOTALSCORE_FIELD_NUMBER: _ClassVar[int]
    PROPERTY1_FIELD_NUMBER: _ClassVar[int]
    CLEARRATEITEMS_FIELD_NUMBER: _ClassVar[int]
    DESCSCORE_FIELD_NUMBER: _ClassVar[int]
    uuid: str
    teamUid: str
    userId: int
    serverName: str
    nickName: str
    userKeys: str
    job: int
    sexJob: int
    grades: int
    fightPower: int
    totalWinCount: int
    teamType: int
    warIndex: int
    curreOrder: int
    result: int
    turnCount: int
    addScore: int
    totalScore: int
    property1: str
    clearRateItems: _containers.RepeatedScalarFieldContainer[int]
    descScore: int
    def __init__(self, uuid: _Optional[str] = ..., teamUid: _Optional[str] = ..., userId: _Optional[int] = ..., serverName: _Optional[str] = ..., nickName: _Optional[str] = ..., userKeys: _Optional[str] = ..., job: _Optional[int] = ..., sexJob: _Optional[int] = ..., grades: _Optional[int] = ..., fightPower: _Optional[int] = ..., totalWinCount: _Optional[int] = ..., teamType: _Optional[int] = ..., warIndex: _Optional[int] = ..., curreOrder: _Optional[int] = ..., result: _Optional[int] = ..., turnCount: _Optional[int] = ..., addScore: _Optional[int] = ..., totalScore: _Optional[int] = ..., property1: _Optional[str] = ..., clearRateItems: _Optional[_Iterable[int]] = ..., descScore: _Optional[int] = ...) -> None: ...

class MateLordsListMsg(_message.Message):
    __slots__ = ("isSign", "isOpen", "order", "eventId", "teamType", "openTime", "totalScore", "altarScore", "inspirLevel", "maxTurnCount", "currentTurn", "leftTime", "info", "masterUserId", "teamUid", "teamName", "warIndex", "serverId", "fashionArm", "fashionWing", "fashionCloth", "fashionHair", "fashionHat", "arm", "job", "nickName", "isOver", "sexJob")
    ISSIGN_FIELD_NUMBER: _ClassVar[int]
    ISOPEN_FIELD_NUMBER: _ClassVar[int]
    ORDER_FIELD_NUMBER: _ClassVar[int]
    EVENTID_FIELD_NUMBER: _ClassVar[int]
    TEAMTYPE_FIELD_NUMBER: _ClassVar[int]
    OPENTIME_FIELD_NUMBER: _ClassVar[int]
    TOTALSCORE_FIELD_NUMBER: _ClassVar[int]
    ALTARSCORE_FIELD_NUMBER: _ClassVar[int]
    INSPIRLEVEL_FIELD_NUMBER: _ClassVar[int]
    MAXTURNCOUNT_FIELD_NUMBER: _ClassVar[int]
    CURRENTTURN_FIELD_NUMBER: _ClassVar[int]
    LEFTTIME_FIELD_NUMBER: _ClassVar[int]
    INFO_FIELD_NUMBER: _ClassVar[int]
    MASTERUSERID_FIELD_NUMBER: _ClassVar[int]
    TEAMUID_FIELD_NUMBER: _ClassVar[int]
    TEAMNAME_FIELD_NUMBER: _ClassVar[int]
    WARINDEX_FIELD_NUMBER: _ClassVar[int]
    SERVERID_FIELD_NUMBER: _ClassVar[int]
    FASHIONARM_FIELD_NUMBER: _ClassVar[int]
    FASHIONWING_FIELD_NUMBER: _ClassVar[int]
    FASHIONCLOTH_FIELD_NUMBER: _ClassVar[int]
    FASHIONHAIR_FIELD_NUMBER: _ClassVar[int]
    FASHIONHAT_FIELD_NUMBER: _ClassVar[int]
    ARM_FIELD_NUMBER: _ClassVar[int]
    JOB_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    ISOVER_FIELD_NUMBER: _ClassVar[int]
    SEXJOB_FIELD_NUMBER: _ClassVar[int]
    isSign: bool
    isOpen: bool
    order: int
    eventId: int
    teamType: int
    openTime: str
    totalScore: int
    altarScore: int
    inspirLevel: int
    maxTurnCount: int
    currentTurn: int
    leftTime: int
    info: _containers.RepeatedCompositeFieldContainer[MateLordsInfoMsg]
    masterUserId: int
    teamUid: str
    teamName: str
    warIndex: int
    serverId: int
    fashionArm: str
    fashionWing: str
    fashionCloth: str
    fashionHair: str
    fashionHat: str
    arm: str
    job: int
    nickName: str
    isOver: bool
    sexJob: int
    def __init__(self, isSign: _Optional[bool] = ..., isOpen: _Optional[bool] = ..., order: _Optional[int] = ..., eventId: _Optional[int] = ..., teamType: _Optional[int] = ..., openTime: _Optional[str] = ..., totalScore: _Optional[int] = ..., altarScore: _Optional[int] = ..., inspirLevel: _Optional[int] = ..., maxTurnCount: _Optional[int] = ..., currentTurn: _Optional[int] = ..., leftTime: _Optional[int] = ..., info: _Optional[_Iterable[_Union[MateLordsInfoMsg, _Mapping]]] = ..., masterUserId: _Optional[int] = ..., teamUid: _Optional[str] = ..., teamName: _Optional[str] = ..., warIndex: _Optional[int] = ..., serverId: _Optional[int] = ..., fashionArm: _Optional[str] = ..., fashionWing: _Optional[str] = ..., fashionCloth: _Optional[str] = ..., fashionHair: _Optional[str] = ..., fashionHat: _Optional[str] = ..., arm: _Optional[str] = ..., job: _Optional[int] = ..., nickName: _Optional[str] = ..., isOver: _Optional[bool] = ..., sexJob: _Optional[int] = ...) -> None: ...

class MemberFightPos(_message.Message):
    __slots__ = ("memberId", "pos")
    MEMBERID_FIELD_NUMBER: _ClassVar[int]
    POS_FIELD_NUMBER: _ClassVar[int]
    memberId: int
    pos: int
    def __init__(self, memberId: _Optional[int] = ..., pos: _Optional[int] = ...) -> None: ...

class MemberFightPosListMsg(_message.Message):
    __slots__ = ("isGet", "memberPos")
    ISGET_FIELD_NUMBER: _ClassVar[int]
    MEMBERPOS_FIELD_NUMBER: _ClassVar[int]
    isGet: bool
    memberPos: _containers.RepeatedCompositeFieldContainer[MemberFightPos]
    def __init__(self, isGet: _Optional[bool] = ..., memberPos: _Optional[_Iterable[_Union[MemberFightPos, _Mapping]]] = ...) -> None: ...

class MessageForSeekMsg(_message.Message):
    __slots__ = ("info",)
    INFO_FIELD_NUMBER: _ClassVar[int]
    info: str
    def __init__(self, info: _Optional[str] = ...) -> None: ...

class MountAvatarMsg(_message.Message):
    __slots__ = ("avatarInfo", "soulScore", "count", "stamp", "totalPage")
    AVATARINFO_FIELD_NUMBER: _ClassVar[int]
    SOULSCORE_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    STAMP_FIELD_NUMBER: _ClassVar[int]
    TOTALPAGE_FIELD_NUMBER: _ClassVar[int]
    avatarInfo: _containers.RepeatedCompositeFieldContainer[AvatarInfoMsg]
    soulScore: int
    count: int
    stamp: int
    totalPage: int
    def __init__(self, avatarInfo: _Optional[_Iterable[_Union[AvatarInfoMsg, _Mapping]]] = ..., soulScore: _Optional[int] = ..., count: _Optional[int] = ..., stamp: _Optional[int] = ..., totalPage: _Optional[int] = ...) -> None: ...

class MountEditMsg(_message.Message):
    __slots__ = ("propertyType", "payType", "param1", "param2", "op")
    PROPERTYTYPE_FIELD_NUMBER: _ClassVar[int]
    PAYTYPE_FIELD_NUMBER: _ClassVar[int]
    PARAM1_FIELD_NUMBER: _ClassVar[int]
    PARAM2_FIELD_NUMBER: _ClassVar[int]
    OP_FIELD_NUMBER: _ClassVar[int]
    propertyType: int
    payType: int
    param1: int
    param2: int
    op: int
    def __init__(self, propertyType: _Optional[int] = ..., payType: _Optional[int] = ..., param1: _Optional[int] = ..., param2: _Optional[int] = ..., op: _Optional[int] = ...) -> None: ...

class MountInfoMsg(_message.Message):
    __slots__ = ("mountTempId", "power", "intellect", "physique", "agility", "speed", "powerGp", "intellectGp", "physiqueGp", "agilityGp", "mountTotalGp", "levelMax", "discount", "mountStarLv", "addPointCount", "refiningSoulPowerGrade", "refiningSoulIntellectGrade", "refiningSoulPhysiqueGrade", "refiningSoulAgilityGrade", "refiningSoulExp")
    MOUNTTEMPID_FIELD_NUMBER: _ClassVar[int]
    POWER_FIELD_NUMBER: _ClassVar[int]
    INTELLECT_FIELD_NUMBER: _ClassVar[int]
    PHYSIQUE_FIELD_NUMBER: _ClassVar[int]
    AGILITY_FIELD_NUMBER: _ClassVar[int]
    SPEED_FIELD_NUMBER: _ClassVar[int]
    POWERGP_FIELD_NUMBER: _ClassVar[int]
    INTELLECTGP_FIELD_NUMBER: _ClassVar[int]
    PHYSIQUEGP_FIELD_NUMBER: _ClassVar[int]
    AGILITYGP_FIELD_NUMBER: _ClassVar[int]
    MOUNTTOTALGP_FIELD_NUMBER: _ClassVar[int]
    LEVELMAX_FIELD_NUMBER: _ClassVar[int]
    DISCOUNT_FIELD_NUMBER: _ClassVar[int]
    MOUNTSTARLV_FIELD_NUMBER: _ClassVar[int]
    ADDPOINTCOUNT_FIELD_NUMBER: _ClassVar[int]
    REFININGSOULPOWERGRADE_FIELD_NUMBER: _ClassVar[int]
    REFININGSOULINTELLECTGRADE_FIELD_NUMBER: _ClassVar[int]
    REFININGSOULPHYSIQUEGRADE_FIELD_NUMBER: _ClassVar[int]
    REFININGSOULAGILITYGRADE_FIELD_NUMBER: _ClassVar[int]
    REFININGSOULEXP_FIELD_NUMBER: _ClassVar[int]
    mountTempId: int
    power: int
    intellect: int
    physique: int
    agility: int
    speed: int
    powerGp: int
    intellectGp: int
    physiqueGp: int
    agilityGp: int
    mountTotalGp: int
    levelMax: int
    discount: int
    mountStarLv: int
    addPointCount: int
    refiningSoulPowerGrade: int
    refiningSoulIntellectGrade: int
    refiningSoulPhysiqueGrade: int
    refiningSoulAgilityGrade: int
    refiningSoulExp: int
    def __init__(self, mountTempId: _Optional[int] = ..., power: _Optional[int] = ..., intellect: _Optional[int] = ..., physique: _Optional[int] = ..., agility: _Optional[int] = ..., speed: _Optional[int] = ..., powerGp: _Optional[int] = ..., intellectGp: _Optional[int] = ..., physiqueGp: _Optional[int] = ..., agilityGp: _Optional[int] = ..., mountTotalGp: _Optional[int] = ..., levelMax: _Optional[int] = ..., discount: _Optional[int] = ..., mountStarLv: _Optional[int] = ..., addPointCount: _Optional[int] = ..., refiningSoulPowerGrade: _Optional[int] = ..., refiningSoulIntellectGrade: _Optional[int] = ..., refiningSoulPhysiqueGrade: _Optional[int] = ..., refiningSoulAgilityGrade: _Optional[int] = ..., refiningSoulExp: _Optional[int] = ...) -> None: ...

class MountKingInfoMsg(_message.Message):
    __slots__ = ("templateId", "extraStar", "level", "gp")
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    EXTRASTAR_FIELD_NUMBER: _ClassVar[int]
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    GP_FIELD_NUMBER: _ClassVar[int]
    templateId: int
    extraStar: int
    level: int
    gp: int
    def __init__(self, templateId: _Optional[int] = ..., extraStar: _Optional[int] = ..., level: _Optional[int] = ..., gp: _Optional[int] = ...) -> None: ...

class MountKingListMsg(_message.Message):
    __slots__ = ("kingList",)
    KINGLIST_FIELD_NUMBER: _ClassVar[int]
    kingList: _containers.RepeatedCompositeFieldContainer[MountKingInfoMsg]
    def __init__(self, kingList: _Optional[_Iterable[_Union[MountKingInfoMsg, _Mapping]]] = ...) -> None: ...

class MountShopItemMsg(_message.Message):
    __slots__ = ("itemTempId", "itemCount", "price", "canBuy")
    ITEMTEMPID_FIELD_NUMBER: _ClassVar[int]
    ITEMCOUNT_FIELD_NUMBER: _ClassVar[int]
    PRICE_FIELD_NUMBER: _ClassVar[int]
    CANBUY_FIELD_NUMBER: _ClassVar[int]
    itemTempId: int
    itemCount: int
    price: int
    canBuy: bool
    def __init__(self, itemTempId: _Optional[int] = ..., itemCount: _Optional[int] = ..., price: _Optional[int] = ..., canBuy: _Optional[bool] = ...) -> None: ...

class MountShopMsg(_message.Message):
    __slots__ = ("itemList",)
    ITEMLIST_FIELD_NUMBER: _ClassVar[int]
    itemList: _containers.RepeatedCompositeFieldContainer[MountShopItemMsg]
    def __init__(self, itemList: _Optional[_Iterable[_Union[MountShopItemMsg, _Mapping]]] = ...) -> None: ...

class MoveFriendReqMsg(_message.Message):
    __slots__ = ("firendId", "groupId", "result")
    FIRENDID_FIELD_NUMBER: _ClassVar[int]
    GROUPID_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    firendId: int
    groupId: int
    result: int
    def __init__(self, firendId: _Optional[int] = ..., groupId: _Optional[int] = ..., result: _Optional[int] = ...) -> None: ...

class MultiCampaignEnterCountMsg(_message.Message):
    __slots__ = ("campaignCount", "campaignMaxcount")
    CAMPAIGNCOUNT_FIELD_NUMBER: _ClassVar[int]
    CAMPAIGNMAXCOUNT_FIELD_NUMBER: _ClassVar[int]
    campaignCount: int
    campaignMaxcount: int
    def __init__(self, campaignCount: _Optional[int] = ..., campaignMaxcount: _Optional[int] = ...) -> None: ...

class MultiCampaignHpSyncMsg(_message.Message):
    __slots__ = ("proxyId", "mapId", "nodeId", "nodeHp", "nodeTotalHp", "playerHp")
    PROXYID_FIELD_NUMBER: _ClassVar[int]
    MAPID_FIELD_NUMBER: _ClassVar[int]
    NODEID_FIELD_NUMBER: _ClassVar[int]
    NODEHP_FIELD_NUMBER: _ClassVar[int]
    NODETOTALHP_FIELD_NUMBER: _ClassVar[int]
    PLAYERHP_FIELD_NUMBER: _ClassVar[int]
    proxyId: str
    mapId: int
    nodeId: int
    nodeHp: int
    nodeTotalHp: int
    playerHp: _containers.RepeatedCompositeFieldContainer[MultiPlayerHpSyncMsg]
    def __init__(self, proxyId: _Optional[str] = ..., mapId: _Optional[int] = ..., nodeId: _Optional[int] = ..., nodeHp: _Optional[int] = ..., nodeTotalHp: _Optional[int] = ..., playerHp: _Optional[_Iterable[_Union[MultiPlayerHpSyncMsg, _Mapping]]] = ...) -> None: ...

class MultiPlayerHpSyncMsg(_message.Message):
    __slots__ = ("armyId", "curHp", "totalHp")
    ARMYID_FIELD_NUMBER: _ClassVar[int]
    CURHP_FIELD_NUMBER: _ClassVar[int]
    TOTALHP_FIELD_NUMBER: _ClassVar[int]
    armyId: int
    curHp: int
    totalHp: int
    def __init__(self, armyId: _Optional[int] = ..., curHp: _Optional[int] = ..., totalHp: _Optional[int] = ...) -> None: ...

class MysteryEventInfoMsg(_message.Message):
    __slots__ = ("id", "userId", "remark", "createTime", "isExist")
    ID_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    REMARK_FIELD_NUMBER: _ClassVar[int]
    CREATETIME_FIELD_NUMBER: _ClassVar[int]
    ISEXIST_FIELD_NUMBER: _ClassVar[int]
    id: int
    userId: int
    remark: str
    createTime: str
    isExist: bool
    def __init__(self, id: _Optional[int] = ..., userId: _Optional[int] = ..., remark: _Optional[str] = ..., createTime: _Optional[str] = ..., isExist: _Optional[bool] = ...) -> None: ...

class MysteryEventListMsg(_message.Message):
    __slots__ = ("eventInfo",)
    EVENTINFO_FIELD_NUMBER: _ClassVar[int]
    eventInfo: _containers.RepeatedCompositeFieldContainer[MysteryEventInfoMsg]
    def __init__(self, eventInfo: _Optional[_Iterable[_Union[MysteryEventInfoMsg, _Mapping]]] = ...) -> None: ...

class NPCChaseMsg(_message.Message):
    __slots__ = ("nodeId", "armyId", "curPosX", "curPosY", "serverName")
    NODEID_FIELD_NUMBER: _ClassVar[int]
    ARMYID_FIELD_NUMBER: _ClassVar[int]
    CURPOSX_FIELD_NUMBER: _ClassVar[int]
    CURPOSY_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    nodeId: int
    armyId: int
    curPosX: int
    curPosY: int
    serverName: str
    def __init__(self, nodeId: _Optional[int] = ..., armyId: _Optional[int] = ..., curPosX: _Optional[int] = ..., curPosY: _Optional[int] = ..., serverName: _Optional[str] = ...) -> None: ...

class NPCChatMsg(_message.Message):
    __slots__ = ("id", "content")
    ID_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    id: int
    content: str
    def __init__(self, id: _Optional[int] = ..., content: _Optional[str] = ...) -> None: ...

class NPCFollowMsg(_message.Message):
    __slots__ = ("escortId", "followId", "curPosX", "curPosY")
    ESCORTID_FIELD_NUMBER: _ClassVar[int]
    FOLLOWID_FIELD_NUMBER: _ClassVar[int]
    CURPOSX_FIELD_NUMBER: _ClassVar[int]
    CURPOSY_FIELD_NUMBER: _ClassVar[int]
    escortId: int
    followId: int
    curPosX: int
    curPosY: int
    def __init__(self, escortId: _Optional[int] = ..., followId: _Optional[int] = ..., curPosX: _Optional[int] = ..., curPosY: _Optional[int] = ...) -> None: ...

class NPCMoveMsg(_message.Message):
    __slots__ = ("id", "posX", "posY", "curPosX", "curPosY")
    ID_FIELD_NUMBER: _ClassVar[int]
    POSX_FIELD_NUMBER: _ClassVar[int]
    POSY_FIELD_NUMBER: _ClassVar[int]
    CURPOSX_FIELD_NUMBER: _ClassVar[int]
    CURPOSY_FIELD_NUMBER: _ClassVar[int]
    id: int
    posX: int
    posY: int
    curPosX: int
    curPosY: int
    def __init__(self, id: _Optional[int] = ..., posX: _Optional[int] = ..., posY: _Optional[int] = ..., curPosX: _Optional[int] = ..., curPosY: _Optional[int] = ...) -> None: ...

class NodeHpListMsg(_message.Message):
    __slots__ = ("campaignId", "campaignType", "nodeHp", "userId")
    CAMPAIGNID_FIELD_NUMBER: _ClassVar[int]
    CAMPAIGNTYPE_FIELD_NUMBER: _ClassVar[int]
    NODEHP_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    campaignId: int
    campaignType: int
    nodeHp: _containers.RepeatedCompositeFieldContainer[NodeHpMsg]
    userId: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, campaignId: _Optional[int] = ..., campaignType: _Optional[int] = ..., nodeHp: _Optional[_Iterable[_Union[NodeHpMsg, _Mapping]]] = ..., userId: _Optional[_Iterable[int]] = ...) -> None: ...

class NodeHpMsg(_message.Message):
    __slots__ = ("nodeId", "currentHp", "totalHp", "param1")
    NODEID_FIELD_NUMBER: _ClassVar[int]
    CURRENTHP_FIELD_NUMBER: _ClassVar[int]
    TOTALHP_FIELD_NUMBER: _ClassVar[int]
    PARAM1_FIELD_NUMBER: _ClassVar[int]
    nodeId: int
    currentHp: int
    totalHp: int
    param1: int
    def __init__(self, nodeId: _Optional[int] = ..., currentHp: _Optional[int] = ..., totalHp: _Optional[int] = ..., param1: _Optional[int] = ...) -> None: ...

class NodeLockReqMsg(_message.Message):
    __slots__ = ("nodeId", "lock")
    NODEID_FIELD_NUMBER: _ClassVar[int]
    LOCK_FIELD_NUMBER: _ClassVar[int]
    nodeId: int
    lock: bool
    def __init__(self, nodeId: _Optional[int] = ..., lock: _Optional[bool] = ...) -> None: ...

class NoviceReqMsgMsg(_message.Message):
    __slots__ = ("noviceProcess", "armyId", "type", "armsId", "goodsId", "gradeProcess")
    NOVICEPROCESS_FIELD_NUMBER: _ClassVar[int]
    ARMYID_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    ARMSID_FIELD_NUMBER: _ClassVar[int]
    GOODSID_FIELD_NUMBER: _ClassVar[int]
    GRADEPROCESS_FIELD_NUMBER: _ClassVar[int]
    noviceProcess: int
    armyId: int
    type: int
    armsId: int
    goodsId: int
    gradeProcess: str
    def __init__(self, noviceProcess: _Optional[int] = ..., armyId: _Optional[int] = ..., type: _Optional[int] = ..., armsId: _Optional[int] = ..., goodsId: _Optional[int] = ..., gradeProcess: _Optional[str] = ...) -> None: ...

class OfflineRewardMsg(_message.Message):
    __slots__ = ("offlineTime", "gpCount", "rateCount", "payType")
    OFFLINETIME_FIELD_NUMBER: _ClassVar[int]
    GPCOUNT_FIELD_NUMBER: _ClassVar[int]
    RATECOUNT_FIELD_NUMBER: _ClassVar[int]
    PAYTYPE_FIELD_NUMBER: _ClassVar[int]
    offlineTime: int
    gpCount: int
    rateCount: int
    payType: int
    def __init__(self, offlineTime: _Optional[int] = ..., gpCount: _Optional[int] = ..., rateCount: _Optional[int] = ..., payType: _Optional[int] = ...) -> None: ...

class OprateReplacemntMsg(_message.Message):
    __slots__ = ("op", "campaignId", "result")
    OP_FIELD_NUMBER: _ClassVar[int]
    CAMPAIGNID_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    op: int
    campaignId: int
    result: int
    def __init__(self, op: _Optional[int] = ..., campaignId: _Optional[int] = ..., result: _Optional[int] = ...) -> None: ...

class OrderInfoMsg(_message.Message):
    __slots__ = ("orderId", "orderType", "remainTime", "userId", "beginTime", "needTime")
    ORDERID_FIELD_NUMBER: _ClassVar[int]
    ORDERTYPE_FIELD_NUMBER: _ClassVar[int]
    REMAINTIME_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    BEGINTIME_FIELD_NUMBER: _ClassVar[int]
    NEEDTIME_FIELD_NUMBER: _ClassVar[int]
    orderId: int
    orderType: int
    remainTime: int
    userId: int
    beginTime: str
    needTime: int
    def __init__(self, orderId: _Optional[int] = ..., orderType: _Optional[int] = ..., remainTime: _Optional[int] = ..., userId: _Optional[int] = ..., beginTime: _Optional[str] = ..., needTime: _Optional[int] = ...) -> None: ...

class OrderQuickRspMsg(_message.Message):
    __slots__ = ("orderInfo",)
    ORDERINFO_FIELD_NUMBER: _ClassVar[int]
    orderInfo: _containers.RepeatedCompositeFieldContainer[OrderInfoMsg]
    def __init__(self, orderInfo: _Optional[_Iterable[_Union[OrderInfoMsg, _Mapping]]] = ...) -> None: ...

class OreActiveBaseInfoMsg(_message.Message):
    __slots__ = ("openTime", "closeTime", "mineOncePrice", "mineTimesPrice", "rewards")
    OPENTIME_FIELD_NUMBER: _ClassVar[int]
    CLOSETIME_FIELD_NUMBER: _ClassVar[int]
    MINEONCEPRICE_FIELD_NUMBER: _ClassVar[int]
    MINETIMESPRICE_FIELD_NUMBER: _ClassVar[int]
    REWARDS_FIELD_NUMBER: _ClassVar[int]
    openTime: str
    closeTime: str
    mineOncePrice: int
    mineTimesPrice: int
    rewards: _containers.RepeatedCompositeFieldContainer[OreRewardTempMsg]
    def __init__(self, openTime: _Optional[str] = ..., closeTime: _Optional[str] = ..., mineOncePrice: _Optional[int] = ..., mineTimesPrice: _Optional[int] = ..., rewards: _Optional[_Iterable[_Union[OreRewardTempMsg, _Mapping]]] = ...) -> None: ...

class OreActiveClientOpMsg(_message.Message):
    __slots__ = ("opType", "isUseProp")
    OPTYPE_FIELD_NUMBER: _ClassVar[int]
    ISUSEPROP_FIELD_NUMBER: _ClassVar[int]
    opType: int
    isUseProp: bool
    def __init__(self, opType: _Optional[int] = ..., isUseProp: _Optional[bool] = ...) -> None: ...

class OreCastle2CrossActiveInfoMsg(_message.Message):
    __slots__ = ("openTime", "closeTime", "dailyMaxTurns", "dailyMaxSpecialRewardTimes", "countDown", "type", "rewards")
    OPENTIME_FIELD_NUMBER: _ClassVar[int]
    CLOSETIME_FIELD_NUMBER: _ClassVar[int]
    DAILYMAXTURNS_FIELD_NUMBER: _ClassVar[int]
    DAILYMAXSPECIALREWARDTIMES_FIELD_NUMBER: _ClassVar[int]
    COUNTDOWN_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    REWARDS_FIELD_NUMBER: _ClassVar[int]
    openTime: str
    closeTime: str
    dailyMaxTurns: int
    dailyMaxSpecialRewardTimes: int
    countDown: int
    type: int
    rewards: _containers.RepeatedCompositeFieldContainer[OreRewardTempMsg]
    def __init__(self, openTime: _Optional[str] = ..., closeTime: _Optional[str] = ..., dailyMaxTurns: _Optional[int] = ..., dailyMaxSpecialRewardTimes: _Optional[int] = ..., countDown: _Optional[int] = ..., type: _Optional[int] = ..., rewards: _Optional[_Iterable[_Union[OreRewardTempMsg, _Mapping]]] = ...) -> None: ...

class OreCross2CastleActiveInfoMsg(_message.Message):
    __slots__ = ("openTime", "closeTime")
    OPENTIME_FIELD_NUMBER: _ClassVar[int]
    CLOSETIME_FIELD_NUMBER: _ClassVar[int]
    openTime: str
    closeTime: str
    def __init__(self, openTime: _Optional[str] = ..., closeTime: _Optional[str] = ...) -> None: ...

class OreItemInfoMsg(_message.Message):
    __slots__ = ("templateId", "count", "name")
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    templateId: int
    count: int
    name: str
    def __init__(self, templateId: _Optional[int] = ..., count: _Optional[int] = ..., name: _Optional[str] = ...) -> None: ...

class OreMineReqMsg(_message.Message):
    __slots__ = ("mineCount", "serverName", "userId", "nickName", "spRewardRemainTimes")
    MINECOUNT_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    SPREWARDREMAINTIMES_FIELD_NUMBER: _ClassVar[int]
    mineCount: int
    serverName: str
    userId: int
    nickName: str
    spRewardRemainTimes: int
    def __init__(self, mineCount: _Optional[int] = ..., serverName: _Optional[str] = ..., userId: _Optional[int] = ..., nickName: _Optional[str] = ..., spRewardRemainTimes: _Optional[int] = ...) -> None: ...

class OreMineRespMsg(_message.Message):
    __slots__ = ("passType", "count", "floors", "infos")
    PASSTYPE_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    FLOORS_FIELD_NUMBER: _ClassVar[int]
    INFOS_FIELD_NUMBER: _ClassVar[int]
    passType: int
    count: int
    floors: _containers.RepeatedScalarFieldContainer[int]
    infos: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, passType: _Optional[int] = ..., count: _Optional[int] = ..., floors: _Optional[_Iterable[int]] = ..., infos: _Optional[_Iterable[str]] = ...) -> None: ...

class OreRewardTempMsg(_message.Message):
    __slots__ = ("rewardType", "specialFloorNum", "rewards")
    REWARDTYPE_FIELD_NUMBER: _ClassVar[int]
    SPECIALFLOORNUM_FIELD_NUMBER: _ClassVar[int]
    REWARDS_FIELD_NUMBER: _ClassVar[int]
    rewardType: int
    specialFloorNum: int
    rewards: _containers.RepeatedCompositeFieldContainer[OreItemInfoMsg]
    def __init__(self, rewardType: _Optional[int] = ..., specialFloorNum: _Optional[int] = ..., rewards: _Optional[_Iterable[_Union[OreItemInfoMsg, _Mapping]]] = ...) -> None: ...

class OreWindowMsg(_message.Message):
    __slots__ = ("todayRemainTurns", "curSeq", "spRewardRemainTimes", "countDown", "mineCount")
    TODAYREMAINTURNS_FIELD_NUMBER: _ClassVar[int]
    CURSEQ_FIELD_NUMBER: _ClassVar[int]
    SPREWARDREMAINTIMES_FIELD_NUMBER: _ClassVar[int]
    COUNTDOWN_FIELD_NUMBER: _ClassVar[int]
    MINECOUNT_FIELD_NUMBER: _ClassVar[int]
    todayRemainTurns: int
    curSeq: int
    spRewardRemainTimes: int
    countDown: int
    mineCount: int
    def __init__(self, todayRemainTurns: _Optional[int] = ..., curSeq: _Optional[int] = ..., spRewardRemainTimes: _Optional[int] = ..., countDown: _Optional[int] = ..., mineCount: _Optional[int] = ...) -> None: ...

class OutercityArmyUpdatedGridMsg(_message.Message):
    __slots__ = ("updatedArmy",)
    UPDATEDARMY_FIELD_NUMBER: _ClassVar[int]
    updatedArmy: _containers.RepeatedCompositeFieldContainer[ArmyArmyMsg]
    def __init__(self, updatedArmy: _Optional[_Iterable[_Union[ArmyArmyMsg, _Mapping]]] = ...) -> None: ...

class OutercityReqMsg(_message.Message):
    __slots__ = ("mapId", "position", "files", "pathArray", "type", "attackCount")
    MAPID_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    FILES_FIELD_NUMBER: _ClassVar[int]
    PATHARRAY_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    ATTACKCOUNT_FIELD_NUMBER: _ClassVar[int]
    mapId: int
    position: str
    files: str
    pathArray: _containers.RepeatedScalarFieldContainer[str]
    type: int
    attackCount: int
    def __init__(self, mapId: _Optional[int] = ..., position: _Optional[str] = ..., files: _Optional[str] = ..., pathArray: _Optional[_Iterable[str]] = ..., type: _Optional[int] = ..., attackCount: _Optional[int] = ...) -> None: ...

class OutercityRspMsg(_message.Message):
    __slots__ = ("result", "startPosX", "startPosY", "curPosX", "curPosY", "endPosX", "endPosY")
    RESULT_FIELD_NUMBER: _ClassVar[int]
    STARTPOSX_FIELD_NUMBER: _ClassVar[int]
    STARTPOSY_FIELD_NUMBER: _ClassVar[int]
    CURPOSX_FIELD_NUMBER: _ClassVar[int]
    CURPOSY_FIELD_NUMBER: _ClassVar[int]
    ENDPOSX_FIELD_NUMBER: _ClassVar[int]
    ENDPOSY_FIELD_NUMBER: _ClassVar[int]
    result: int
    startPosX: int
    startPosY: int
    curPosX: int
    curPosY: int
    endPosX: int
    endPosY: int
    def __init__(self, result: _Optional[int] = ..., startPosX: _Optional[int] = ..., startPosY: _Optional[int] = ..., curPosX: _Optional[int] = ..., curPosY: _Optional[int] = ..., endPosX: _Optional[int] = ..., endPosY: _Optional[int] = ...) -> None: ...

class PackageConditionMsg(_message.Message):
    __slots__ = ("conditionId", "conditionValue", "conditionBak", "conditionBak2", "conditionBak3", "conditionBak4")
    CONDITIONID_FIELD_NUMBER: _ClassVar[int]
    CONDITIONVALUE_FIELD_NUMBER: _ClassVar[int]
    CONDITIONBAK_FIELD_NUMBER: _ClassVar[int]
    CONDITIONBAK2_FIELD_NUMBER: _ClassVar[int]
    CONDITIONBAK3_FIELD_NUMBER: _ClassVar[int]
    CONDITIONBAK4_FIELD_NUMBER: _ClassVar[int]
    conditionId: int
    conditionValue: int
    conditionBak: int
    conditionBak2: int
    conditionBak3: int
    conditionBak4: int
    def __init__(self, conditionId: _Optional[int] = ..., conditionValue: _Optional[int] = ..., conditionBak: _Optional[int] = ..., conditionBak2: _Optional[int] = ..., conditionBak3: _Optional[int] = ..., conditionBak4: _Optional[int] = ...) -> None: ...

class PackageData(_message.Message):
    __slots__ = ("packId", "status", "countDown", "isShow", "param1", "finishValue", "getCount")
    PACKID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    COUNTDOWN_FIELD_NUMBER: _ClassVar[int]
    ISSHOW_FIELD_NUMBER: _ClassVar[int]
    PARAM1_FIELD_NUMBER: _ClassVar[int]
    FINISHVALUE_FIELD_NUMBER: _ClassVar[int]
    GETCOUNT_FIELD_NUMBER: _ClassVar[int]
    packId: str
    status: int
    countDown: int
    isShow: bool
    param1: str
    finishValue: int
    getCount: int
    def __init__(self, packId: _Optional[str] = ..., status: _Optional[int] = ..., countDown: _Optional[int] = ..., isShow: _Optional[bool] = ..., param1: _Optional[str] = ..., finishValue: _Optional[int] = ..., getCount: _Optional[int] = ...) -> None: ...

class PackageInfoMsg(_message.Message):
    __slots__ = ("packageId", "order", "point", "price", "itemid1", "count1", "itemid2", "count2", "itemid3", "count3", "itemid4", "count4", "itemid5", "count5", "itemid6", "count6", "itemid7", "count7", "count8", "itemid8")
    PACKAGEID_FIELD_NUMBER: _ClassVar[int]
    ORDER_FIELD_NUMBER: _ClassVar[int]
    POINT_FIELD_NUMBER: _ClassVar[int]
    PRICE_FIELD_NUMBER: _ClassVar[int]
    ITEMID1_FIELD_NUMBER: _ClassVar[int]
    COUNT1_FIELD_NUMBER: _ClassVar[int]
    ITEMID2_FIELD_NUMBER: _ClassVar[int]
    COUNT2_FIELD_NUMBER: _ClassVar[int]
    ITEMID3_FIELD_NUMBER: _ClassVar[int]
    COUNT3_FIELD_NUMBER: _ClassVar[int]
    ITEMID4_FIELD_NUMBER: _ClassVar[int]
    COUNT4_FIELD_NUMBER: _ClassVar[int]
    ITEMID5_FIELD_NUMBER: _ClassVar[int]
    COUNT5_FIELD_NUMBER: _ClassVar[int]
    ITEMID6_FIELD_NUMBER: _ClassVar[int]
    COUNT6_FIELD_NUMBER: _ClassVar[int]
    ITEMID7_FIELD_NUMBER: _ClassVar[int]
    COUNT7_FIELD_NUMBER: _ClassVar[int]
    COUNT8_FIELD_NUMBER: _ClassVar[int]
    ITEMID8_FIELD_NUMBER: _ClassVar[int]
    packageId: str
    order: int
    point: int
    price: int
    itemid1: int
    count1: int
    itemid2: int
    count2: int
    itemid3: int
    count3: int
    itemid4: int
    count4: int
    itemid5: int
    count5: int
    itemid6: int
    count6: int
    itemid7: int
    count7: int
    count8: int
    itemid8: int
    def __init__(self, packageId: _Optional[str] = ..., order: _Optional[int] = ..., point: _Optional[int] = ..., price: _Optional[int] = ..., itemid1: _Optional[int] = ..., count1: _Optional[int] = ..., itemid2: _Optional[int] = ..., count2: _Optional[int] = ..., itemid3: _Optional[int] = ..., count3: _Optional[int] = ..., itemid4: _Optional[int] = ..., count4: _Optional[int] = ..., itemid5: _Optional[int] = ..., count5: _Optional[int] = ..., itemid6: _Optional[int] = ..., count6: _Optional[int] = ..., itemid7: _Optional[int] = ..., count7: _Optional[int] = ..., count8: _Optional[int] = ..., itemid8: _Optional[int] = ...) -> None: ...

class PackageStateMsg(_message.Message):
    __slots__ = ("id", "isget")
    ID_FIELD_NUMBER: _ClassVar[int]
    ISGET_FIELD_NUMBER: _ClassVar[int]
    id: str
    isget: bool
    def __init__(self, id: _Optional[str] = ..., isget: _Optional[bool] = ...) -> None: ...

class PawnChangeMsg(_message.Message):
    __slots__ = ("curPawnTempId", "tarPawnTempId", "payType")
    CURPAWNTEMPID_FIELD_NUMBER: _ClassVar[int]
    TARPAWNTEMPID_FIELD_NUMBER: _ClassVar[int]
    PAYTYPE_FIELD_NUMBER: _ClassVar[int]
    curPawnTempId: int
    tarPawnTempId: int
    payType: int
    def __init__(self, curPawnTempId: _Optional[int] = ..., tarPawnTempId: _Optional[int] = ..., payType: _Optional[int] = ...) -> None: ...

class PayTypeMsg(_message.Message):
    __slots__ = ("payType", "property1", "property2", "type")
    PAYTYPE_FIELD_NUMBER: _ClassVar[int]
    PROPERTY1_FIELD_NUMBER: _ClassVar[int]
    PROPERTY2_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    payType: int
    property1: int
    property2: int
    type: int
    def __init__(self, payType: _Optional[int] = ..., property1: _Optional[int] = ..., property2: _Optional[int] = ..., type: _Optional[int] = ...) -> None: ...

class PetChallengeInfoMsg(_message.Message):
    __slots__ = ("playerInfo", "playerPets", "challengeLog")
    PLAYERINFO_FIELD_NUMBER: _ClassVar[int]
    PLAYERPETS_FIELD_NUMBER: _ClassVar[int]
    CHALLENGELOG_FIELD_NUMBER: _ClassVar[int]
    playerInfo: PetChallengePlayerMsg
    playerPets: _containers.RepeatedCompositeFieldContainer[PlayerPetMsg]
    challengeLog: _containers.RepeatedCompositeFieldContainer[PetChallengeLogMsg]
    def __init__(self, playerInfo: _Optional[_Union[PetChallengePlayerMsg, _Mapping]] = ..., playerPets: _Optional[_Iterable[_Union[PlayerPetMsg, _Mapping]]] = ..., challengeLog: _Optional[_Iterable[_Union[PetChallengeLogMsg, _Mapping]]] = ...) -> None: ...

class PetChallengeLogMsg(_message.Message):
    __slots__ = ("userId", "tarUserId", "tarNickName", "result", "isAttack", "logDate", "score", "tarPets")
    USERID_FIELD_NUMBER: _ClassVar[int]
    TARUSERID_FIELD_NUMBER: _ClassVar[int]
    TARNICKNAME_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    ISATTACK_FIELD_NUMBER: _ClassVar[int]
    LOGDATE_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    TARPETS_FIELD_NUMBER: _ClassVar[int]
    userId: int
    tarUserId: int
    tarNickName: str
    result: int
    isAttack: bool
    logDate: str
    score: int
    tarPets: PlayerPetMsg
    def __init__(self, userId: _Optional[int] = ..., tarUserId: _Optional[int] = ..., tarNickName: _Optional[str] = ..., result: _Optional[int] = ..., isAttack: _Optional[bool] = ..., logDate: _Optional[str] = ..., score: _Optional[int] = ..., tarPets: _Optional[_Union[PlayerPetMsg, _Mapping]] = ...) -> None: ...

class PetChallengePlayerMsg(_message.Message):
    __slots__ = ("leftTime", "challengeCount", "totalCount", "score", "order")
    LEFTTIME_FIELD_NUMBER: _ClassVar[int]
    CHALLENGECOUNT_FIELD_NUMBER: _ClassVar[int]
    TOTALCOUNT_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    ORDER_FIELD_NUMBER: _ClassVar[int]
    leftTime: int
    challengeCount: int
    totalCount: int
    score: int
    order: int
    def __init__(self, leftTime: _Optional[int] = ..., challengeCount: _Optional[int] = ..., totalCount: _Optional[int] = ..., score: _Optional[int] = ..., order: _Optional[int] = ...) -> None: ...

class PetEquipmentMsg(_message.Message):
    __slots__ = ("templateId", "pos", "join1", "join2", "join3", "join4", "randomSkill1", "randomSkill2", "randomSkill3", "randomSkill4", "randomSkill5", "mouldGrade", "isBind")
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    POS_FIELD_NUMBER: _ClassVar[int]
    JOIN1_FIELD_NUMBER: _ClassVar[int]
    JOIN2_FIELD_NUMBER: _ClassVar[int]
    JOIN3_FIELD_NUMBER: _ClassVar[int]
    JOIN4_FIELD_NUMBER: _ClassVar[int]
    RANDOMSKILL1_FIELD_NUMBER: _ClassVar[int]
    RANDOMSKILL2_FIELD_NUMBER: _ClassVar[int]
    RANDOMSKILL3_FIELD_NUMBER: _ClassVar[int]
    RANDOMSKILL4_FIELD_NUMBER: _ClassVar[int]
    RANDOMSKILL5_FIELD_NUMBER: _ClassVar[int]
    MOULDGRADE_FIELD_NUMBER: _ClassVar[int]
    ISBIND_FIELD_NUMBER: _ClassVar[int]
    templateId: int
    pos: int
    join1: int
    join2: int
    join3: int
    join4: int
    randomSkill1: int
    randomSkill2: int
    randomSkill3: int
    randomSkill4: int
    randomSkill5: int
    mouldGrade: int
    isBind: bool
    def __init__(self, templateId: _Optional[int] = ..., pos: _Optional[int] = ..., join1: _Optional[int] = ..., join2: _Optional[int] = ..., join3: _Optional[int] = ..., join4: _Optional[int] = ..., randomSkill1: _Optional[int] = ..., randomSkill2: _Optional[int] = ..., randomSkill3: _Optional[int] = ..., randomSkill4: _Optional[int] = ..., randomSkill5: _Optional[int] = ..., mouldGrade: _Optional[int] = ..., isBind: _Optional[bool] = ...) -> None: ...

class PetInfoMsg(_message.Message):
    __slots__ = ("petId", "templateId", "petName", "curGp", "curGrade", "power", "intel", "physi", "armor", "remainPoints", "initPowerApti", "initIntelApti", "initPhysiApti", "initArmorApti", "powerApti", "intelApti", "physiApti", "armorApti", "curQualityGp", "growthRate", "maxHp", "fireResi", "waterResi", "electResi", "windResi", "darkResi", "lightResi", "followSkills", "changeSkills", "isFight", "isPractice", "isBind", "totalGp", "fightingCapacity", "isDel", "quality", "isGuard", "chaSkillIndexs", "fastKey", "initQuality", "isLocked", "bagAttack", "bagDefence", "bagMagicattack", "bagMagicdefence", "bagLiving", "nextPowerApti", "nextIntelApti", "nextPhysiApti", "nextArmorApti")
    PETID_FIELD_NUMBER: _ClassVar[int]
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    PETNAME_FIELD_NUMBER: _ClassVar[int]
    CURGP_FIELD_NUMBER: _ClassVar[int]
    CURGRADE_FIELD_NUMBER: _ClassVar[int]
    POWER_FIELD_NUMBER: _ClassVar[int]
    INTEL_FIELD_NUMBER: _ClassVar[int]
    PHYSI_FIELD_NUMBER: _ClassVar[int]
    ARMOR_FIELD_NUMBER: _ClassVar[int]
    REMAINPOINTS_FIELD_NUMBER: _ClassVar[int]
    INITPOWERAPTI_FIELD_NUMBER: _ClassVar[int]
    INITINTELAPTI_FIELD_NUMBER: _ClassVar[int]
    INITPHYSIAPTI_FIELD_NUMBER: _ClassVar[int]
    INITARMORAPTI_FIELD_NUMBER: _ClassVar[int]
    POWERAPTI_FIELD_NUMBER: _ClassVar[int]
    INTELAPTI_FIELD_NUMBER: _ClassVar[int]
    PHYSIAPTI_FIELD_NUMBER: _ClassVar[int]
    ARMORAPTI_FIELD_NUMBER: _ClassVar[int]
    CURQUALITYGP_FIELD_NUMBER: _ClassVar[int]
    GROWTHRATE_FIELD_NUMBER: _ClassVar[int]
    MAXHP_FIELD_NUMBER: _ClassVar[int]
    FIRERESI_FIELD_NUMBER: _ClassVar[int]
    WATERRESI_FIELD_NUMBER: _ClassVar[int]
    ELECTRESI_FIELD_NUMBER: _ClassVar[int]
    WINDRESI_FIELD_NUMBER: _ClassVar[int]
    DARKRESI_FIELD_NUMBER: _ClassVar[int]
    LIGHTRESI_FIELD_NUMBER: _ClassVar[int]
    FOLLOWSKILLS_FIELD_NUMBER: _ClassVar[int]
    CHANGESKILLS_FIELD_NUMBER: _ClassVar[int]
    ISFIGHT_FIELD_NUMBER: _ClassVar[int]
    ISPRACTICE_FIELD_NUMBER: _ClassVar[int]
    ISBIND_FIELD_NUMBER: _ClassVar[int]
    TOTALGP_FIELD_NUMBER: _ClassVar[int]
    FIGHTINGCAPACITY_FIELD_NUMBER: _ClassVar[int]
    ISDEL_FIELD_NUMBER: _ClassVar[int]
    QUALITY_FIELD_NUMBER: _ClassVar[int]
    ISGUARD_FIELD_NUMBER: _ClassVar[int]
    CHASKILLINDEXS_FIELD_NUMBER: _ClassVar[int]
    FASTKEY_FIELD_NUMBER: _ClassVar[int]
    INITQUALITY_FIELD_NUMBER: _ClassVar[int]
    ISLOCKED_FIELD_NUMBER: _ClassVar[int]
    BAGATTACK_FIELD_NUMBER: _ClassVar[int]
    BAGDEFENCE_FIELD_NUMBER: _ClassVar[int]
    BAGMAGICATTACK_FIELD_NUMBER: _ClassVar[int]
    BAGMAGICDEFENCE_FIELD_NUMBER: _ClassVar[int]
    BAGLIVING_FIELD_NUMBER: _ClassVar[int]
    NEXTPOWERAPTI_FIELD_NUMBER: _ClassVar[int]
    NEXTINTELAPTI_FIELD_NUMBER: _ClassVar[int]
    NEXTPHYSIAPTI_FIELD_NUMBER: _ClassVar[int]
    NEXTARMORAPTI_FIELD_NUMBER: _ClassVar[int]
    petId: int
    templateId: int
    petName: str
    curGp: int
    curGrade: int
    power: int
    intel: int
    physi: int
    armor: int
    remainPoints: int
    initPowerApti: int
    initIntelApti: int
    initPhysiApti: int
    initArmorApti: int
    powerApti: int
    intelApti: int
    physiApti: int
    armorApti: int
    curQualityGp: int
    growthRate: int
    maxHp: int
    fireResi: int
    waterResi: int
    electResi: int
    windResi: int
    darkResi: int
    lightResi: int
    followSkills: str
    changeSkills: str
    isFight: bool
    isPractice: bool
    isBind: bool
    totalGp: int
    fightingCapacity: int
    isDel: bool
    quality: int
    isGuard: bool
    chaSkillIndexs: str
    fastKey: str
    initQuality: int
    isLocked: bool
    bagAttack: int
    bagDefence: int
    bagMagicattack: int
    bagMagicdefence: int
    bagLiving: int
    nextPowerApti: int
    nextIntelApti: int
    nextPhysiApti: int
    nextArmorApti: int
    def __init__(self, petId: _Optional[int] = ..., templateId: _Optional[int] = ..., petName: _Optional[str] = ..., curGp: _Optional[int] = ..., curGrade: _Optional[int] = ..., power: _Optional[int] = ..., intel: _Optional[int] = ..., physi: _Optional[int] = ..., armor: _Optional[int] = ..., remainPoints: _Optional[int] = ..., initPowerApti: _Optional[int] = ..., initIntelApti: _Optional[int] = ..., initPhysiApti: _Optional[int] = ..., initArmorApti: _Optional[int] = ..., powerApti: _Optional[int] = ..., intelApti: _Optional[int] = ..., physiApti: _Optional[int] = ..., armorApti: _Optional[int] = ..., curQualityGp: _Optional[int] = ..., growthRate: _Optional[int] = ..., maxHp: _Optional[int] = ..., fireResi: _Optional[int] = ..., waterResi: _Optional[int] = ..., electResi: _Optional[int] = ..., windResi: _Optional[int] = ..., darkResi: _Optional[int] = ..., lightResi: _Optional[int] = ..., followSkills: _Optional[str] = ..., changeSkills: _Optional[str] = ..., isFight: _Optional[bool] = ..., isPractice: _Optional[bool] = ..., isBind: _Optional[bool] = ..., totalGp: _Optional[int] = ..., fightingCapacity: _Optional[int] = ..., isDel: _Optional[bool] = ..., quality: _Optional[int] = ..., isGuard: _Optional[bool] = ..., chaSkillIndexs: _Optional[str] = ..., fastKey: _Optional[str] = ..., initQuality: _Optional[int] = ..., isLocked: _Optional[bool] = ..., bagAttack: _Optional[int] = ..., bagDefence: _Optional[int] = ..., bagMagicattack: _Optional[int] = ..., bagMagicdefence: _Optional[int] = ..., bagLiving: _Optional[int] = ..., nextPowerApti: _Optional[int] = ..., nextIntelApti: _Optional[int] = ..., nextPhysiApti: _Optional[int] = ..., nextArmorApti: _Optional[int] = ...) -> None: ...

class PetIslandDefendStateMsg(_message.Message):
    __slots__ = ("leftTime", "mapId", "bossId", "peaceMiddle", "peaceHigh", "peaceBoss", "ragePoint")
    LEFTTIME_FIELD_NUMBER: _ClassVar[int]
    MAPID_FIELD_NUMBER: _ClassVar[int]
    BOSSID_FIELD_NUMBER: _ClassVar[int]
    PEACEMIDDLE_FIELD_NUMBER: _ClassVar[int]
    PEACEHIGH_FIELD_NUMBER: _ClassVar[int]
    PEACEBOSS_FIELD_NUMBER: _ClassVar[int]
    RAGEPOINT_FIELD_NUMBER: _ClassVar[int]
    leftTime: int
    mapId: int
    bossId: int
    peaceMiddle: int
    peaceHigh: int
    peaceBoss: int
    ragePoint: int
    def __init__(self, leftTime: _Optional[int] = ..., mapId: _Optional[int] = ..., bossId: _Optional[int] = ..., peaceMiddle: _Optional[int] = ..., peaceHigh: _Optional[int] = ..., peaceBoss: _Optional[int] = ..., ragePoint: _Optional[int] = ...) -> None: ...

class PhysicListUpdateMsg(_message.Message):
    __slots__ = ("reqGrid", "wildLand", "baseCastle")
    REQGRID_FIELD_NUMBER: _ClassVar[int]
    WILDLAND_FIELD_NUMBER: _ClassVar[int]
    BASECASTLE_FIELD_NUMBER: _ClassVar[int]
    reqGrid: str
    wildLand: _containers.RepeatedCompositeFieldContainer[WildLandMsg]
    baseCastle: _containers.RepeatedCompositeFieldContainer[BaseCastleMsg]
    def __init__(self, reqGrid: _Optional[str] = ..., wildLand: _Optional[_Iterable[_Union[WildLandMsg, _Mapping]]] = ..., baseCastle: _Optional[_Iterable[_Union[BaseCastleMsg, _Mapping]]] = ...) -> None: ...

class PhysicUpdateReqMsg(_message.Message):
    __slots__ = ("reqGrid", "mapId")
    REQGRID_FIELD_NUMBER: _ClassVar[int]
    MAPID_FIELD_NUMBER: _ClassVar[int]
    reqGrid: str
    mapId: int
    def __init__(self, reqGrid: _Optional[str] = ..., mapId: _Optional[int] = ...) -> None: ...

class PickupResult(_message.Message):
    __slots__ = ("mailId", "attachIndex", "result")
    MAILID_FIELD_NUMBER: _ClassVar[int]
    ATTACHINDEX_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    mailId: int
    attachIndex: int
    result: bool
    def __init__(self, mailId: _Optional[int] = ..., attachIndex: _Optional[int] = ..., result: _Optional[bool] = ...) -> None: ...

class PlaceStateRspMsg(_message.Message):
    __slots__ = ("placeState",)
    PLACESTATE_FIELD_NUMBER: _ClassVar[int]
    placeState: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, placeState: _Optional[_Iterable[int]] = ...) -> None: ...

class PlayerAASRefreshMsg(_message.Message):
    __slots__ = ("aasOnlineTime", "isCloseAAS", "sysSwitch")
    AASONLINETIME_FIELD_NUMBER: _ClassVar[int]
    ISCLOSEAAS_FIELD_NUMBER: _ClassVar[int]
    SYSSWITCH_FIELD_NUMBER: _ClassVar[int]
    aasOnlineTime: int
    isCloseAAS: bool
    sysSwitch: bool
    def __init__(self, aasOnlineTime: _Optional[int] = ..., isCloseAAS: _Optional[bool] = ..., sysSwitch: _Optional[bool] = ...) -> None: ...

class PlayerAASReqMsg(_message.Message):
    __slots__ = ("cardName", "cardId")
    CARDNAME_FIELD_NUMBER: _ClassVar[int]
    CARDID_FIELD_NUMBER: _ClassVar[int]
    cardName: str
    cardId: str
    def __init__(self, cardName: _Optional[str] = ..., cardId: _Optional[str] = ...) -> None: ...

class PlayerAASRspMsg(_message.Message):
    __slots__ = ("result", "age", "cardId")
    RESULT_FIELD_NUMBER: _ClassVar[int]
    AGE_FIELD_NUMBER: _ClassVar[int]
    CARDID_FIELD_NUMBER: _ClassVar[int]
    result: bool
    age: int
    cardId: str
    def __init__(self, result: _Optional[bool] = ..., age: _Optional[int] = ..., cardId: _Optional[str] = ...) -> None: ...

class PlayerActiveReqMsg(_message.Message):
    __slots__ = ("key", "activeId")
    KEY_FIELD_NUMBER: _ClassVar[int]
    ACTIVEID_FIELD_NUMBER: _ClassVar[int]
    key: str
    activeId: str
    def __init__(self, key: _Optional[str] = ..., activeId: _Optional[str] = ...) -> None: ...

class PlayerActiveRspMsg(_message.Message):
    __slots__ = ("result", "activeid")
    RESULT_FIELD_NUMBER: _ClassVar[int]
    ACTIVEID_FIELD_NUMBER: _ClassVar[int]
    result: int
    activeid: str
    def __init__(self, result: _Optional[int] = ..., activeid: _Optional[str] = ...) -> None: ...

class PlayerBottleMsg(_message.Message):
    __slots__ = ("userId", "nickName", "isVip", "state")
    USERID_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    ISVIP_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    userId: int
    nickName: str
    isVip: bool
    state: int
    def __init__(self, userId: _Optional[int] = ..., nickName: _Optional[str] = ..., isVip: _Optional[bool] = ..., state: _Optional[int] = ...) -> None: ...

class PlayerChallengeMsg(_message.Message):
    __slots__ = ("tarUserId", "tarArmyId", "payType", "type")
    TARUSERID_FIELD_NUMBER: _ClassVar[int]
    TARARMYID_FIELD_NUMBER: _ClassVar[int]
    PAYTYPE_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    tarUserId: int
    tarArmyId: int
    payType: int
    type: int
    def __init__(self, tarUserId: _Optional[int] = ..., tarArmyId: _Optional[int] = ..., payType: _Optional[int] = ..., type: _Optional[int] = ...) -> None: ...

class PlayerChildInfoMsg(_message.Message):
    __slots__ = ("child",)
    CHILD_FIELD_NUMBER: _ClassVar[int]
    child: _containers.RepeatedCompositeFieldContainer[ChildrenInfoMsg]
    def __init__(self, child: _Optional[_Iterable[_Union[ChildrenInfoMsg, _Mapping]]] = ...) -> None: ...

class PlayerDataMsg(_message.Message):
    __slots__ = ("user", "castle", "army", "quest", "build", "tree", "aas", "smith", "bag", "leed", "star", "friend", "effect", "sys", "offline", "reward", "tower", "shop", "challReward", "snsReq", "active", "switches", "sweep", "questionnarie", "kingContract", "rebateCharge", "rebateConsum", "sumActive", "crossScoreReward", "appell", "bottle", "petChallengeReward", "powcardInfo")
    USER_FIELD_NUMBER: _ClassVar[int]
    CASTLE_FIELD_NUMBER: _ClassVar[int]
    ARMY_FIELD_NUMBER: _ClassVar[int]
    QUEST_FIELD_NUMBER: _ClassVar[int]
    BUILD_FIELD_NUMBER: _ClassVar[int]
    TREE_FIELD_NUMBER: _ClassVar[int]
    AAS_FIELD_NUMBER: _ClassVar[int]
    SMITH_FIELD_NUMBER: _ClassVar[int]
    BAG_FIELD_NUMBER: _ClassVar[int]
    LEED_FIELD_NUMBER: _ClassVar[int]
    STAR_FIELD_NUMBER: _ClassVar[int]
    FRIEND_FIELD_NUMBER: _ClassVar[int]
    EFFECT_FIELD_NUMBER: _ClassVar[int]
    SYS_FIELD_NUMBER: _ClassVar[int]
    OFFLINE_FIELD_NUMBER: _ClassVar[int]
    REWARD_FIELD_NUMBER: _ClassVar[int]
    TOWER_FIELD_NUMBER: _ClassVar[int]
    SHOP_FIELD_NUMBER: _ClassVar[int]
    CHALLREWARD_FIELD_NUMBER: _ClassVar[int]
    SNSREQ_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_FIELD_NUMBER: _ClassVar[int]
    SWITCHES_FIELD_NUMBER: _ClassVar[int]
    SWEEP_FIELD_NUMBER: _ClassVar[int]
    QUESTIONNARIE_FIELD_NUMBER: _ClassVar[int]
    KINGCONTRACT_FIELD_NUMBER: _ClassVar[int]
    REBATECHARGE_FIELD_NUMBER: _ClassVar[int]
    REBATECONSUM_FIELD_NUMBER: _ClassVar[int]
    SUMACTIVE_FIELD_NUMBER: _ClassVar[int]
    CROSSSCOREREWARD_FIELD_NUMBER: _ClassVar[int]
    APPELL_FIELD_NUMBER: _ClassVar[int]
    BOTTLE_FIELD_NUMBER: _ClassVar[int]
    PETCHALLENGEREWARD_FIELD_NUMBER: _ClassVar[int]
    POWCARDINFO_FIELD_NUMBER: _ClassVar[int]
    user: bool
    castle: bool
    army: bool
    quest: bool
    build: bool
    tree: bool
    aas: bool
    smith: bool
    bag: bool
    leed: bool
    star: bool
    friend: bool
    effect: bool
    sys: bool
    offline: bool
    reward: bool
    tower: bool
    shop: bool
    challReward: bool
    snsReq: bool
    active: bool
    switches: bool
    sweep: bool
    questionnarie: bool
    kingContract: bool
    rebateCharge: bool
    rebateConsum: bool
    sumActive: bool
    crossScoreReward: bool
    appell: bool
    bottle: bool
    petChallengeReward: bool
    powcardInfo: bool
    def __init__(self, user: _Optional[bool] = ..., castle: _Optional[bool] = ..., army: _Optional[bool] = ..., quest: _Optional[bool] = ..., build: _Optional[bool] = ..., tree: _Optional[bool] = ..., aas: _Optional[bool] = ..., smith: _Optional[bool] = ..., bag: _Optional[bool] = ..., leed: _Optional[bool] = ..., star: _Optional[bool] = ..., friend: _Optional[bool] = ..., effect: _Optional[bool] = ..., sys: _Optional[bool] = ..., offline: _Optional[bool] = ..., reward: _Optional[bool] = ..., tower: _Optional[bool] = ..., shop: _Optional[bool] = ..., challReward: _Optional[bool] = ..., snsReq: _Optional[bool] = ..., active: _Optional[bool] = ..., switches: _Optional[bool] = ..., sweep: _Optional[bool] = ..., questionnarie: _Optional[bool] = ..., kingContract: _Optional[bool] = ..., rebateCharge: _Optional[bool] = ..., rebateConsum: _Optional[bool] = ..., sumActive: _Optional[bool] = ..., crossScoreReward: _Optional[bool] = ..., appell: _Optional[bool] = ..., bottle: _Optional[bool] = ..., petChallengeReward: _Optional[bool] = ..., powcardInfo: _Optional[bool] = ...) -> None: ...

class PlayerHangupStateListMsg(_message.Message):
    __slots__ = ("hanupState",)
    HANUPSTATE_FIELD_NUMBER: _ClassVar[int]
    hanupState: _containers.RepeatedCompositeFieldContainer[PlayerHangupStateMsg]
    def __init__(self, hanupState: _Optional[_Iterable[_Union[PlayerHangupStateMsg, _Mapping]]] = ...) -> None: ...

class PlayerHangupStateMsg(_message.Message):
    __slots__ = ("armyId", "state")
    ARMYID_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    armyId: int
    state: int
    def __init__(self, armyId: _Optional[int] = ..., state: _Optional[int] = ...) -> None: ...

class PlayerInfoNoticeMsg(_message.Message):
    __slots__ = ("affectGeste", "score", "isAdd", "playerState", "isTips", "serverName", "manualExit", "mountTemplateId", "mountGrade", "wing", "arm", "cloth", "changeShapeId", "hat", "fashionArm", "fashionCloth", "hide", "crossScore", "gesteJoin", "appellId", "petTemplateId", "petName", "petQuality", "gestePowcardJoin")
    AFFECTGESTE_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    ISADD_FIELD_NUMBER: _ClassVar[int]
    PLAYERSTATE_FIELD_NUMBER: _ClassVar[int]
    ISTIPS_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    MANUALEXIT_FIELD_NUMBER: _ClassVar[int]
    MOUNTTEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    MOUNTGRADE_FIELD_NUMBER: _ClassVar[int]
    WING_FIELD_NUMBER: _ClassVar[int]
    ARM_FIELD_NUMBER: _ClassVar[int]
    CLOTH_FIELD_NUMBER: _ClassVar[int]
    CHANGESHAPEID_FIELD_NUMBER: _ClassVar[int]
    HAT_FIELD_NUMBER: _ClassVar[int]
    FASHIONARM_FIELD_NUMBER: _ClassVar[int]
    FASHIONCLOTH_FIELD_NUMBER: _ClassVar[int]
    HIDE_FIELD_NUMBER: _ClassVar[int]
    CROSSSCORE_FIELD_NUMBER: _ClassVar[int]
    GESTEJOIN_FIELD_NUMBER: _ClassVar[int]
    APPELLID_FIELD_NUMBER: _ClassVar[int]
    PETTEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    PETNAME_FIELD_NUMBER: _ClassVar[int]
    PETQUALITY_FIELD_NUMBER: _ClassVar[int]
    GESTEPOWCARDJOIN_FIELD_NUMBER: _ClassVar[int]
    affectGeste: int
    score: int
    isAdd: bool
    playerState: int
    isTips: bool
    serverName: str
    manualExit: bool
    mountTemplateId: int
    mountGrade: int
    wing: str
    arm: str
    cloth: str
    changeShapeId: int
    hat: str
    fashionArm: str
    fashionCloth: str
    hide: bool
    crossScore: int
    gesteJoin: int
    appellId: int
    petTemplateId: int
    petName: str
    petQuality: int
    gestePowcardJoin: int
    def __init__(self, affectGeste: _Optional[int] = ..., score: _Optional[int] = ..., isAdd: _Optional[bool] = ..., playerState: _Optional[int] = ..., isTips: _Optional[bool] = ..., serverName: _Optional[str] = ..., manualExit: _Optional[bool] = ..., mountTemplateId: _Optional[int] = ..., mountGrade: _Optional[int] = ..., wing: _Optional[str] = ..., arm: _Optional[str] = ..., cloth: _Optional[str] = ..., changeShapeId: _Optional[int] = ..., hat: _Optional[str] = ..., fashionArm: _Optional[str] = ..., fashionCloth: _Optional[str] = ..., hide: _Optional[bool] = ..., crossScore: _Optional[int] = ..., gesteJoin: _Optional[int] = ..., appellId: _Optional[int] = ..., petTemplateId: _Optional[int] = ..., petName: _Optional[str] = ..., petQuality: _Optional[int] = ..., gestePowcardJoin: _Optional[int] = ...) -> None: ...

class PlayerLuckyMsg(_message.Message):
    __slots__ = ("luckyCount", "remainCount", "lastReceive", "point", "gold")
    LUCKYCOUNT_FIELD_NUMBER: _ClassVar[int]
    REMAINCOUNT_FIELD_NUMBER: _ClassVar[int]
    LASTRECEIVE_FIELD_NUMBER: _ClassVar[int]
    POINT_FIELD_NUMBER: _ClassVar[int]
    GOLD_FIELD_NUMBER: _ClassVar[int]
    luckyCount: int
    remainCount: int
    lastReceive: bytes
    point: int
    gold: int
    def __init__(self, luckyCount: _Optional[int] = ..., remainCount: _Optional[int] = ..., lastReceive: _Optional[bytes] = ..., point: _Optional[int] = ..., gold: _Optional[int] = ...) -> None: ...

class PlayerMoveCameraMsg(_message.Message):
    __slots__ = ("scene", "targetX", "targetY", "delay")
    SCENE_FIELD_NUMBER: _ClassVar[int]
    TARGETX_FIELD_NUMBER: _ClassVar[int]
    TARGETY_FIELD_NUMBER: _ClassVar[int]
    DELAY_FIELD_NUMBER: _ClassVar[int]
    scene: str
    targetX: int
    targetY: int
    delay: int
    def __init__(self, scene: _Optional[str] = ..., targetX: _Optional[int] = ..., targetY: _Optional[int] = ..., delay: _Optional[int] = ...) -> None: ...

class PlayerMoveMsg(_message.Message):
    __slots__ = ("userId", "mapId", "tarX", "tarY", "ismoveCamera")
    USERID_FIELD_NUMBER: _ClassVar[int]
    MAPID_FIELD_NUMBER: _ClassVar[int]
    TARX_FIELD_NUMBER: _ClassVar[int]
    TARY_FIELD_NUMBER: _ClassVar[int]
    ISMOVECAMERA_FIELD_NUMBER: _ClassVar[int]
    userId: int
    mapId: int
    tarX: int
    tarY: int
    ismoveCamera: bool
    def __init__(self, userId: _Optional[int] = ..., mapId: _Optional[int] = ..., tarX: _Optional[int] = ..., tarY: _Optional[int] = ..., ismoveCamera: _Optional[bool] = ...) -> None: ...

class PlayerMovieMsg(_message.Message):
    __slots__ = ("movieTargetType", "targetId", "movieType", "delay", "mapId")
    MOVIETARGETTYPE_FIELD_NUMBER: _ClassVar[int]
    TARGETID_FIELD_NUMBER: _ClassVar[int]
    MOVIETYPE_FIELD_NUMBER: _ClassVar[int]
    DELAY_FIELD_NUMBER: _ClassVar[int]
    MAPID_FIELD_NUMBER: _ClassVar[int]
    movieTargetType: int
    targetId: int
    movieType: str
    delay: int
    mapId: int
    def __init__(self, movieTargetType: _Optional[int] = ..., targetId: _Optional[int] = ..., movieType: _Optional[str] = ..., delay: _Optional[int] = ..., mapId: _Optional[int] = ...) -> None: ...

class PlayerMsg(_message.Message):
    __slots__ = ("playerId", "nickName", "sex", "pic", "camp", "point", "giftToken", "state", "lastAward", "questSiteLen", "questSite", "consortiaId", "consortiaName", "claimId", "claimName", "grades", "gp", "repute", "consortiaOffer", "strategy", "weary", "attackLeftCount", "noviceProcess", "consortiaAttack", "consortiaDefence", "consortiaAgility", "consortiaAbility", "consortiaCaptain", "gpOrder", "fightingCapacity", "gradeProcess", "timeProcess", "timeGet", "campaignSite", "bagCount", "matchWin", "matchFailed", "consortiaGold", "consortiaPhysique", "right", "job", "leedProcess", "starCount", "signDate", "signTimes", "signSite", "order", "startFree", "totalGp", "refuseFriend", "refuseInvite", "consortiaTotaloffer", "showVersion", "campaignCount", "timeRun", "qteGuide", "starpoint", "isAuto", "lastOutConsortia", "geste", "storeGrade", "storeGp", "reloginProcess", "reloginCount", "blessingCount", "blessingBuff", "blessingMaxCount", "firstCharge", "charm", "matchRoomCount", "kingBuff", "leaveGp", "altarConsortiaId", "serverName", "rewardTimes", "warFieldCount", "trialCount", "appellId", "crossScore", "trialMaxCount", "wearyLimit", "lordsScore", "isReceived", "mineScore", "isBackPlayer", "refuseTeamInvite", "campaignMaxcount", "expLimit", "hasVicePassword", "isDuringToResetTime", "leadExtractTimes", "lastFreeSkillLearnTime", "rentalBagTime", "status")
    PLAYERID_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    SEX_FIELD_NUMBER: _ClassVar[int]
    PIC_FIELD_NUMBER: _ClassVar[int]
    CAMP_FIELD_NUMBER: _ClassVar[int]
    POINT_FIELD_NUMBER: _ClassVar[int]
    GIFTTOKEN_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    LASTAWARD_FIELD_NUMBER: _ClassVar[int]
    QUESTSITELEN_FIELD_NUMBER: _ClassVar[int]
    QUESTSITE_FIELD_NUMBER: _ClassVar[int]
    CONSORTIAID_FIELD_NUMBER: _ClassVar[int]
    CONSORTIANAME_FIELD_NUMBER: _ClassVar[int]
    CLAIMID_FIELD_NUMBER: _ClassVar[int]
    CLAIMNAME_FIELD_NUMBER: _ClassVar[int]
    GRADES_FIELD_NUMBER: _ClassVar[int]
    GP_FIELD_NUMBER: _ClassVar[int]
    REPUTE_FIELD_NUMBER: _ClassVar[int]
    CONSORTIAOFFER_FIELD_NUMBER: _ClassVar[int]
    STRATEGY_FIELD_NUMBER: _ClassVar[int]
    WEARY_FIELD_NUMBER: _ClassVar[int]
    ATTACKLEFTCOUNT_FIELD_NUMBER: _ClassVar[int]
    NOVICEPROCESS_FIELD_NUMBER: _ClassVar[int]
    CONSORTIAATTACK_FIELD_NUMBER: _ClassVar[int]
    CONSORTIADEFENCE_FIELD_NUMBER: _ClassVar[int]
    CONSORTIAAGILITY_FIELD_NUMBER: _ClassVar[int]
    CONSORTIAABILITY_FIELD_NUMBER: _ClassVar[int]
    CONSORTIACAPTAIN_FIELD_NUMBER: _ClassVar[int]
    GPORDER_FIELD_NUMBER: _ClassVar[int]
    FIGHTINGCAPACITY_FIELD_NUMBER: _ClassVar[int]
    GRADEPROCESS_FIELD_NUMBER: _ClassVar[int]
    TIMEPROCESS_FIELD_NUMBER: _ClassVar[int]
    TIMEGET_FIELD_NUMBER: _ClassVar[int]
    CAMPAIGNSITE_FIELD_NUMBER: _ClassVar[int]
    BAGCOUNT_FIELD_NUMBER: _ClassVar[int]
    MATCHWIN_FIELD_NUMBER: _ClassVar[int]
    MATCHFAILED_FIELD_NUMBER: _ClassVar[int]
    CONSORTIAGOLD_FIELD_NUMBER: _ClassVar[int]
    CONSORTIAPHYSIQUE_FIELD_NUMBER: _ClassVar[int]
    RIGHT_FIELD_NUMBER: _ClassVar[int]
    JOB_FIELD_NUMBER: _ClassVar[int]
    LEEDPROCESS_FIELD_NUMBER: _ClassVar[int]
    STARCOUNT_FIELD_NUMBER: _ClassVar[int]
    SIGNDATE_FIELD_NUMBER: _ClassVar[int]
    SIGNTIMES_FIELD_NUMBER: _ClassVar[int]
    SIGNSITE_FIELD_NUMBER: _ClassVar[int]
    ORDER_FIELD_NUMBER: _ClassVar[int]
    STARTFREE_FIELD_NUMBER: _ClassVar[int]
    TOTALGP_FIELD_NUMBER: _ClassVar[int]
    REFUSEFRIEND_FIELD_NUMBER: _ClassVar[int]
    REFUSEINVITE_FIELD_NUMBER: _ClassVar[int]
    CONSORTIATOTALOFFER_FIELD_NUMBER: _ClassVar[int]
    SHOWVERSION_FIELD_NUMBER: _ClassVar[int]
    CAMPAIGNCOUNT_FIELD_NUMBER: _ClassVar[int]
    TIMERUN_FIELD_NUMBER: _ClassVar[int]
    QTEGUIDE_FIELD_NUMBER: _ClassVar[int]
    STARPOINT_FIELD_NUMBER: _ClassVar[int]
    ISAUTO_FIELD_NUMBER: _ClassVar[int]
    LASTOUTCONSORTIA_FIELD_NUMBER: _ClassVar[int]
    GESTE_FIELD_NUMBER: _ClassVar[int]
    STOREGRADE_FIELD_NUMBER: _ClassVar[int]
    STOREGP_FIELD_NUMBER: _ClassVar[int]
    RELOGINPROCESS_FIELD_NUMBER: _ClassVar[int]
    RELOGINCOUNT_FIELD_NUMBER: _ClassVar[int]
    BLESSINGCOUNT_FIELD_NUMBER: _ClassVar[int]
    BLESSINGBUFF_FIELD_NUMBER: _ClassVar[int]
    BLESSINGMAXCOUNT_FIELD_NUMBER: _ClassVar[int]
    FIRSTCHARGE_FIELD_NUMBER: _ClassVar[int]
    CHARM_FIELD_NUMBER: _ClassVar[int]
    MATCHROOMCOUNT_FIELD_NUMBER: _ClassVar[int]
    KINGBUFF_FIELD_NUMBER: _ClassVar[int]
    LEAVEGP_FIELD_NUMBER: _ClassVar[int]
    ALTARCONSORTIAID_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    REWARDTIMES_FIELD_NUMBER: _ClassVar[int]
    WARFIELDCOUNT_FIELD_NUMBER: _ClassVar[int]
    TRIALCOUNT_FIELD_NUMBER: _ClassVar[int]
    APPELLID_FIELD_NUMBER: _ClassVar[int]
    CROSSSCORE_FIELD_NUMBER: _ClassVar[int]
    TRIALMAXCOUNT_FIELD_NUMBER: _ClassVar[int]
    WEARYLIMIT_FIELD_NUMBER: _ClassVar[int]
    LORDSSCORE_FIELD_NUMBER: _ClassVar[int]
    ISRECEIVED_FIELD_NUMBER: _ClassVar[int]
    MINESCORE_FIELD_NUMBER: _ClassVar[int]
    ISBACKPLAYER_FIELD_NUMBER: _ClassVar[int]
    REFUSETEAMINVITE_FIELD_NUMBER: _ClassVar[int]
    CAMPAIGNMAXCOUNT_FIELD_NUMBER: _ClassVar[int]
    EXPLIMIT_FIELD_NUMBER: _ClassVar[int]
    HASVICEPASSWORD_FIELD_NUMBER: _ClassVar[int]
    ISDURINGTORESETTIME_FIELD_NUMBER: _ClassVar[int]
    LEADEXTRACTTIMES_FIELD_NUMBER: _ClassVar[int]
    LASTFREESKILLLEARNTIME_FIELD_NUMBER: _ClassVar[int]
    RENTALBAGTIME_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    playerId: int
    nickName: str
    sex: int
    pic: int
    camp: int
    point: int
    giftToken: int
    state: int
    lastAward: str
    questSiteLen: int
    questSite: bytes
    consortiaId: int
    consortiaName: str
    claimId: int
    claimName: str
    grades: int
    gp: int
    repute: int
    consortiaOffer: int
    strategy: int
    weary: int
    attackLeftCount: int
    noviceProcess: int
    consortiaAttack: int
    consortiaDefence: int
    consortiaAgility: int
    consortiaAbility: int
    consortiaCaptain: int
    gpOrder: int
    fightingCapacity: int
    gradeProcess: str
    timeProcess: int
    timeGet: bool
    campaignSite: str
    bagCount: int
    matchWin: int
    matchFailed: int
    consortiaGold: int
    consortiaPhysique: int
    right: int
    job: int
    leedProcess: int
    starCount: int
    signDate: str
    signTimes: int
    signSite: int
    order: PlayerOrderMsg
    startFree: int
    totalGp: int
    refuseFriend: bool
    refuseInvite: bool
    consortiaTotaloffer: int
    showVersion: bool
    campaignCount: int
    timeRun: int
    qteGuide: int
    starpoint: int
    isAuto: bool
    lastOutConsortia: str
    geste: int
    storeGrade: int
    storeGp: int
    reloginProcess: int
    reloginCount: int
    blessingCount: int
    blessingBuff: int
    blessingMaxCount: int
    firstCharge: bool
    charm: int
    matchRoomCount: int
    kingBuff: bool
    leaveGp: int
    altarConsortiaId: int
    serverName: str
    rewardTimes: int
    warFieldCount: int
    trialCount: int
    appellId: int
    crossScore: int
    trialMaxCount: int
    wearyLimit: int
    lordsScore: int
    isReceived: bool
    mineScore: int
    isBackPlayer: bool
    refuseTeamInvite: bool
    campaignMaxcount: int
    expLimit: int
    hasVicePassword: int
    isDuringToResetTime: int
    leadExtractTimes: int
    lastFreeSkillLearnTime: str
    rentalBagTime: str
    status: int
    def __init__(self, playerId: _Optional[int] = ..., nickName: _Optional[str] = ..., sex: _Optional[int] = ..., pic: _Optional[int] = ..., camp: _Optional[int] = ..., point: _Optional[int] = ..., giftToken: _Optional[int] = ..., state: _Optional[int] = ..., lastAward: _Optional[str] = ..., questSiteLen: _Optional[int] = ..., questSite: _Optional[bytes] = ..., consortiaId: _Optional[int] = ..., consortiaName: _Optional[str] = ..., claimId: _Optional[int] = ..., claimName: _Optional[str] = ..., grades: _Optional[int] = ..., gp: _Optional[int] = ..., repute: _Optional[int] = ..., consortiaOffer: _Optional[int] = ..., strategy: _Optional[int] = ..., weary: _Optional[int] = ..., attackLeftCount: _Optional[int] = ..., noviceProcess: _Optional[int] = ..., consortiaAttack: _Optional[int] = ..., consortiaDefence: _Optional[int] = ..., consortiaAgility: _Optional[int] = ..., consortiaAbility: _Optional[int] = ..., consortiaCaptain: _Optional[int] = ..., gpOrder: _Optional[int] = ..., fightingCapacity: _Optional[int] = ..., gradeProcess: _Optional[str] = ..., timeProcess: _Optional[int] = ..., timeGet: _Optional[bool] = ..., campaignSite: _Optional[str] = ..., bagCount: _Optional[int] = ..., matchWin: _Optional[int] = ..., matchFailed: _Optional[int] = ..., consortiaGold: _Optional[int] = ..., consortiaPhysique: _Optional[int] = ..., right: _Optional[int] = ..., job: _Optional[int] = ..., leedProcess: _Optional[int] = ..., starCount: _Optional[int] = ..., signDate: _Optional[str] = ..., signTimes: _Optional[int] = ..., signSite: _Optional[int] = ..., order: _Optional[_Union[PlayerOrderMsg, _Mapping]] = ..., startFree: _Optional[int] = ..., totalGp: _Optional[int] = ..., refuseFriend: _Optional[bool] = ..., refuseInvite: _Optional[bool] = ..., consortiaTotaloffer: _Optional[int] = ..., showVersion: _Optional[bool] = ..., campaignCount: _Optional[int] = ..., timeRun: _Optional[int] = ..., qteGuide: _Optional[int] = ..., starpoint: _Optional[int] = ..., isAuto: _Optional[bool] = ..., lastOutConsortia: _Optional[str] = ..., geste: _Optional[int] = ..., storeGrade: _Optional[int] = ..., storeGp: _Optional[int] = ..., reloginProcess: _Optional[int] = ..., reloginCount: _Optional[int] = ..., blessingCount: _Optional[int] = ..., blessingBuff: _Optional[int] = ..., blessingMaxCount: _Optional[int] = ..., firstCharge: _Optional[bool] = ..., charm: _Optional[int] = ..., matchRoomCount: _Optional[int] = ..., kingBuff: _Optional[bool] = ..., leaveGp: _Optional[int] = ..., altarConsortiaId: _Optional[int] = ..., serverName: _Optional[str] = ..., rewardTimes: _Optional[int] = ..., warFieldCount: _Optional[int] = ..., trialCount: _Optional[int] = ..., appellId: _Optional[int] = ..., crossScore: _Optional[int] = ..., trialMaxCount: _Optional[int] = ..., wearyLimit: _Optional[int] = ..., lordsScore: _Optional[int] = ..., isReceived: _Optional[bool] = ..., mineScore: _Optional[int] = ..., isBackPlayer: _Optional[bool] = ..., refuseTeamInvite: _Optional[bool] = ..., campaignMaxcount: _Optional[int] = ..., expLimit: _Optional[int] = ..., hasVicePassword: _Optional[int] = ..., isDuringToResetTime: _Optional[int] = ..., leadExtractTimes: _Optional[int] = ..., lastFreeSkillLearnTime: _Optional[str] = ..., rentalBagTime: _Optional[str] = ..., status: _Optional[int] = ...) -> None: ...

class PlayerMutualRspMsg(_message.Message):
    __slots__ = ("userId", "serverName", "type", "param")
    USERID_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    PARAM_FIELD_NUMBER: _ClassVar[int]
    userId: int
    serverName: str
    type: int
    param: str
    def __init__(self, userId: _Optional[int] = ..., serverName: _Optional[str] = ..., type: _Optional[int] = ..., param: _Optional[str] = ...) -> None: ...

class PlayerNodeStateMsg(_message.Message):
    __slots__ = ("mapId", "nodeId", "isStand", "armyId")
    MAPID_FIELD_NUMBER: _ClassVar[int]
    NODEID_FIELD_NUMBER: _ClassVar[int]
    ISSTAND_FIELD_NUMBER: _ClassVar[int]
    ARMYID_FIELD_NUMBER: _ClassVar[int]
    mapId: int
    nodeId: int
    isStand: bool
    armyId: int
    def __init__(self, mapId: _Optional[int] = ..., nodeId: _Optional[int] = ..., isStand: _Optional[bool] = ..., armyId: _Optional[int] = ...) -> None: ...

class PlayerOrderMsg(_message.Message):
    __slots__ = ("playerId", "fightCapacityOrder", "geste_Order", "charm_Order", "soulScore_Order")
    PLAYERID_FIELD_NUMBER: _ClassVar[int]
    FIGHTCAPACITYORDER_FIELD_NUMBER: _ClassVar[int]
    GESTE_ORDER_FIELD_NUMBER: _ClassVar[int]
    CHARM_ORDER_FIELD_NUMBER: _ClassVar[int]
    SOULSCORE_ORDER_FIELD_NUMBER: _ClassVar[int]
    playerId: int
    fightCapacityOrder: int
    geste_Order: int
    charm_Order: int
    soulScore_Order: int
    def __init__(self, playerId: _Optional[int] = ..., fightCapacityOrder: _Optional[int] = ..., geste_Order: _Optional[int] = ..., charm_Order: _Optional[int] = ..., soulScore_Order: _Optional[int] = ...) -> None: ...

class PlayerPetMsg(_message.Message):
    __slots__ = ("userId", "petInfo", "nickName", "order", "chaPos", "score", "petCount", "equipmets")
    USERID_FIELD_NUMBER: _ClassVar[int]
    PETINFO_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    ORDER_FIELD_NUMBER: _ClassVar[int]
    CHAPOS_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    PETCOUNT_FIELD_NUMBER: _ClassVar[int]
    EQUIPMETS_FIELD_NUMBER: _ClassVar[int]
    userId: int
    petInfo: _containers.RepeatedCompositeFieldContainer[PetInfoMsg]
    nickName: str
    order: int
    chaPos: str
    score: int
    petCount: int
    equipmets: _containers.RepeatedCompositeFieldContainer[PetEquipmentMsg]
    def __init__(self, userId: _Optional[int] = ..., petInfo: _Optional[_Iterable[_Union[PetInfoMsg, _Mapping]]] = ..., nickName: _Optional[str] = ..., order: _Optional[int] = ..., chaPos: _Optional[str] = ..., score: _Optional[int] = ..., petCount: _Optional[int] = ..., equipmets: _Optional[_Iterable[_Union[PetEquipmentMsg, _Mapping]]] = ...) -> None: ...

class PlayerPetOpMsg(_message.Message):
    __slots__ = ("petId", "opType", "petName", "attributes", "value", "itemPos", "payType", "skillId", "fightType")
    PETID_FIELD_NUMBER: _ClassVar[int]
    OPTYPE_FIELD_NUMBER: _ClassVar[int]
    PETNAME_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    ITEMPOS_FIELD_NUMBER: _ClassVar[int]
    PAYTYPE_FIELD_NUMBER: _ClassVar[int]
    SKILLID_FIELD_NUMBER: _ClassVar[int]
    FIGHTTYPE_FIELD_NUMBER: _ClassVar[int]
    petId: int
    opType: int
    petName: str
    attributes: _containers.RepeatedScalarFieldContainer[int]
    value: int
    itemPos: int
    payType: int
    skillId: int
    fightType: int
    def __init__(self, petId: _Optional[int] = ..., opType: _Optional[int] = ..., petName: _Optional[str] = ..., attributes: _Optional[_Iterable[int]] = ..., value: _Optional[int] = ..., itemPos: _Optional[int] = ..., payType: _Optional[int] = ..., skillId: _Optional[int] = ..., fightType: _Optional[int] = ...) -> None: ...

class PlayerReadyRspMsg(_message.Message):
    __slots__ = ("readyState",)
    READYSTATE_FIELD_NUMBER: _ClassVar[int]
    readyState: _containers.RepeatedCompositeFieldContainer[PlayerreadyrspmsgPlayerReady]
    def __init__(self, readyState: _Optional[_Iterable[_Union[PlayerreadyrspmsgPlayerReady, _Mapping]]] = ...) -> None: ...

class PlayerRefiningSoulMsg(_message.Message):
    __slots__ = ("count", "remainCount", "point", "soul")
    COUNT_FIELD_NUMBER: _ClassVar[int]
    REMAINCOUNT_FIELD_NUMBER: _ClassVar[int]
    POINT_FIELD_NUMBER: _ClassVar[int]
    SOUL_FIELD_NUMBER: _ClassVar[int]
    count: int
    remainCount: int
    point: int
    soul: int
    def __init__(self, count: _Optional[int] = ..., remainCount: _Optional[int] = ..., point: _Optional[int] = ..., soul: _Optional[int] = ...) -> None: ...

class PlayerRenameReqMsg(_message.Message):
    __slots__ = ("nickName", "type", "pos")
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    POS_FIELD_NUMBER: _ClassVar[int]
    nickName: str
    type: int
    pos: int
    def __init__(self, nickName: _Optional[str] = ..., type: _Optional[int] = ..., pos: _Optional[int] = ...) -> None: ...

class PlayerRenameRspMsg(_message.Message):
    __slots__ = ("result",)
    RESULT_FIELD_NUMBER: _ClassVar[int]
    result: bool
    def __init__(self, result: _Optional[bool] = ...) -> None: ...

class PlayerSeekInfoMsg(_message.Message):
    __slots__ = ("seekCount", "nextAddTime", "state", "eventDesc", "curNodeId", "op", "seekNodeList")
    SEEKCOUNT_FIELD_NUMBER: _ClassVar[int]
    NEXTADDTIME_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    EVENTDESC_FIELD_NUMBER: _ClassVar[int]
    CURNODEID_FIELD_NUMBER: _ClassVar[int]
    OP_FIELD_NUMBER: _ClassVar[int]
    SEEKNODELIST_FIELD_NUMBER: _ClassVar[int]
    seekCount: int
    nextAddTime: int
    state: int
    eventDesc: str
    curNodeId: int
    op: int
    seekNodeList: SeekNodeListMsg
    def __init__(self, seekCount: _Optional[int] = ..., nextAddTime: _Optional[int] = ..., state: _Optional[int] = ..., eventDesc: _Optional[str] = ..., curNodeId: _Optional[int] = ..., op: _Optional[int] = ..., seekNodeList: _Optional[_Union[SeekNodeListMsg, _Mapping]] = ...) -> None: ...

class PlayerSignRspMsg(_message.Message):
    __slots__ = ("signDate", "signTimes", "signSite")
    SIGNDATE_FIELD_NUMBER: _ClassVar[int]
    SIGNTIMES_FIELD_NUMBER: _ClassVar[int]
    SIGNSITE_FIELD_NUMBER: _ClassVar[int]
    signDate: str
    signTimes: int
    signSite: int
    def __init__(self, signDate: _Optional[str] = ..., signTimes: _Optional[int] = ..., signSite: _Optional[int] = ...) -> None: ...

class PlayerStateListMsg(_message.Message):
    __slots__ = ("playerState", "userId")
    PLAYERSTATE_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    playerState: _containers.RepeatedCompositeFieldContainer[WorldBossPlayerStateMsg]
    userId: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, playerState: _Optional[_Iterable[_Union[WorldBossPlayerStateMsg, _Mapping]]] = ..., userId: _Optional[_Iterable[int]] = ...) -> None: ...

class PlayerTokenInfoMsg(_message.Message):
    __slots__ = ("tokenInfos",)
    TOKENINFOS_FIELD_NUMBER: _ClassVar[int]
    tokenInfos: _containers.RepeatedCompositeFieldContainer[TokenInfoMsg]
    def __init__(self, tokenInfos: _Optional[_Iterable[_Union[TokenInfoMsg, _Mapping]]] = ...) -> None: ...

class PlayerTreasureMsg(_message.Message):
    __slots__ = ("userId", "joinCount", "rewardCount", "index", "templateIds", "opType", "payType", "refreshType", "isReward", "isFirstQuest", "isFirstGet", "isFirstUse")
    USERID_FIELD_NUMBER: _ClassVar[int]
    JOINCOUNT_FIELD_NUMBER: _ClassVar[int]
    REWARDCOUNT_FIELD_NUMBER: _ClassVar[int]
    INDEX_FIELD_NUMBER: _ClassVar[int]
    TEMPLATEIDS_FIELD_NUMBER: _ClassVar[int]
    OPTYPE_FIELD_NUMBER: _ClassVar[int]
    PAYTYPE_FIELD_NUMBER: _ClassVar[int]
    REFRESHTYPE_FIELD_NUMBER: _ClassVar[int]
    ISREWARD_FIELD_NUMBER: _ClassVar[int]
    ISFIRSTQUEST_FIELD_NUMBER: _ClassVar[int]
    ISFIRSTGET_FIELD_NUMBER: _ClassVar[int]
    ISFIRSTUSE_FIELD_NUMBER: _ClassVar[int]
    userId: int
    joinCount: int
    rewardCount: int
    index: int
    templateIds: _containers.RepeatedScalarFieldContainer[int]
    opType: int
    payType: int
    refreshType: bool
    isReward: bool
    isFirstQuest: bool
    isFirstGet: bool
    isFirstUse: bool
    def __init__(self, userId: _Optional[int] = ..., joinCount: _Optional[int] = ..., rewardCount: _Optional[int] = ..., index: _Optional[int] = ..., templateIds: _Optional[_Iterable[int]] = ..., opType: _Optional[int] = ..., payType: _Optional[int] = ..., refreshType: _Optional[bool] = ..., isReward: _Optional[bool] = ..., isFirstQuest: _Optional[bool] = ..., isFirstGet: _Optional[bool] = ..., isFirstUse: _Optional[bool] = ...) -> None: ...

class PlayerTrialMsg(_message.Message):
    __slots__ = ("userId", "trialInfos", "param1", "param2", "param3", "param4")
    USERID_FIELD_NUMBER: _ClassVar[int]
    TRIALINFOS_FIELD_NUMBER: _ClassVar[int]
    PARAM1_FIELD_NUMBER: _ClassVar[int]
    PARAM2_FIELD_NUMBER: _ClassVar[int]
    PARAM3_FIELD_NUMBER: _ClassVar[int]
    PARAM4_FIELD_NUMBER: _ClassVar[int]
    userId: int
    trialInfos: _containers.RepeatedCompositeFieldContainer[TrialInfoMsg]
    param1: int
    param2: int
    param3: int
    param4: int
    def __init__(self, userId: _Optional[int] = ..., trialInfos: _Optional[_Iterable[_Union[TrialInfoMsg, _Mapping]]] = ..., param1: _Optional[int] = ..., param2: _Optional[int] = ..., param3: _Optional[int] = ..., param4: _Optional[int] = ...) -> None: ...

class PlayerVehicleListMsg(_message.Message):
    __slots__ = ("vehicles",)
    VEHICLES_FIELD_NUMBER: _ClassVar[int]
    vehicles: _containers.RepeatedCompositeFieldContainer[PlayerVehicleMsg]
    def __init__(self, vehicles: _Optional[_Iterable[_Union[PlayerVehicleMsg, _Mapping]]] = ...) -> None: ...

class PlayerVehicleMsg(_message.Message):
    __slots__ = ("id", "templateId", "hp", "team", "buffState", "grade", "name", "head", "x", "y", "playerId", "consortia", "vip", "appellId", "rebornTime", "npcNodeId", "serverName", "transGrade", "isBackPlayer", "maxHp", "defaultSkills", "isHoldKey")
    ID_FIELD_NUMBER: _ClassVar[int]
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    HP_FIELD_NUMBER: _ClassVar[int]
    TEAM_FIELD_NUMBER: _ClassVar[int]
    BUFFSTATE_FIELD_NUMBER: _ClassVar[int]
    GRADE_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    HEAD_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    PLAYERID_FIELD_NUMBER: _ClassVar[int]
    CONSORTIA_FIELD_NUMBER: _ClassVar[int]
    VIP_FIELD_NUMBER: _ClassVar[int]
    APPELLID_FIELD_NUMBER: _ClassVar[int]
    REBORNTIME_FIELD_NUMBER: _ClassVar[int]
    NPCNODEID_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    TRANSGRADE_FIELD_NUMBER: _ClassVar[int]
    ISBACKPLAYER_FIELD_NUMBER: _ClassVar[int]
    MAXHP_FIELD_NUMBER: _ClassVar[int]
    DEFAULTSKILLS_FIELD_NUMBER: _ClassVar[int]
    ISHOLDKEY_FIELD_NUMBER: _ClassVar[int]
    id: int
    templateId: int
    hp: int
    team: int
    buffState: _containers.RepeatedScalarFieldContainer[int]
    grade: int
    name: str
    head: int
    x: int
    y: int
    playerId: int
    consortia: str
    vip: int
    appellId: int
    rebornTime: int
    npcNodeId: int
    serverName: str
    transGrade: int
    isBackPlayer: bool
    maxHp: int
    defaultSkills: str
    isHoldKey: bool
    def __init__(self, id: _Optional[int] = ..., templateId: _Optional[int] = ..., hp: _Optional[int] = ..., team: _Optional[int] = ..., buffState: _Optional[_Iterable[int]] = ..., grade: _Optional[int] = ..., name: _Optional[str] = ..., head: _Optional[int] = ..., x: _Optional[int] = ..., y: _Optional[int] = ..., playerId: _Optional[int] = ..., consortia: _Optional[str] = ..., vip: _Optional[int] = ..., appellId: _Optional[int] = ..., rebornTime: _Optional[int] = ..., npcNodeId: _Optional[int] = ..., serverName: _Optional[str] = ..., transGrade: _Optional[int] = ..., isBackPlayer: _Optional[bool] = ..., maxHp: _Optional[int] = ..., defaultSkills: _Optional[str] = ..., isHoldKey: _Optional[bool] = ...) -> None: ...

class PlayerVehicleProfileMsg(_message.Message):
    __slots__ = ("exp", "score", "defaultVehicle", "isFirst")
    EXP_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    DEFAULTVEHICLE_FIELD_NUMBER: _ClassVar[int]
    ISFIRST_FIELD_NUMBER: _ClassVar[int]
    exp: int
    score: int
    defaultVehicle: int
    isFirst: bool
    def __init__(self, exp: _Optional[int] = ..., score: _Optional[int] = ..., defaultVehicle: _Optional[int] = ..., isFirst: _Optional[bool] = ...) -> None: ...

class PlayerreadyrspmsgPlayerReady(_message.Message):
    __slots__ = ("playerId", "readyState")
    PLAYERID_FIELD_NUMBER: _ClassVar[int]
    READYSTATE_FIELD_NUMBER: _ClassVar[int]
    playerId: int
    readyState: int
    def __init__(self, playerId: _Optional[int] = ..., readyState: _Optional[int] = ...) -> None: ...

class PlotInfoMsg(_message.Message):
    __slots__ = ("index", "direction", "roleId", "roleName", "event", "param", "text", "delayTime")
    INDEX_FIELD_NUMBER: _ClassVar[int]
    DIRECTION_FIELD_NUMBER: _ClassVar[int]
    ROLEID_FIELD_NUMBER: _ClassVar[int]
    ROLENAME_FIELD_NUMBER: _ClassVar[int]
    EVENT_FIELD_NUMBER: _ClassVar[int]
    PARAM_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    DELAYTIME_FIELD_NUMBER: _ClassVar[int]
    index: int
    direction: int
    roleId: int
    roleName: str
    event: str
    param: str
    text: str
    delayTime: int
    def __init__(self, index: _Optional[int] = ..., direction: _Optional[int] = ..., roleId: _Optional[int] = ..., roleName: _Optional[str] = ..., event: _Optional[str] = ..., param: _Optional[str] = ..., text: _Optional[str] = ..., delayTime: _Optional[int] = ...) -> None: ...

class PlotMsg(_message.Message):
    __slots__ = ("loop", "sceneType", "info")
    LOOP_FIELD_NUMBER: _ClassVar[int]
    SCENETYPE_FIELD_NUMBER: _ClassVar[int]
    INFO_FIELD_NUMBER: _ClassVar[int]
    loop: bool
    sceneType: int
    info: _containers.RepeatedCompositeFieldContainer[PlotInfoMsg]
    def __init__(self, loop: _Optional[bool] = ..., sceneType: _Optional[int] = ..., info: _Optional[_Iterable[_Union[PlotInfoMsg, _Mapping]]] = ...) -> None: ...

class PolishInfoMsg(_message.Message):
    __slots__ = ("sontype", "level", "exp")
    SONTYPE_FIELD_NUMBER: _ClassVar[int]
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    EXP_FIELD_NUMBER: _ClassVar[int]
    sontype: int
    level: int
    exp: int
    def __init__(self, sontype: _Optional[int] = ..., level: _Optional[int] = ..., exp: _Optional[int] = ...) -> None: ...

class PosMoveMsg(_message.Message):
    __slots__ = ("mapId", "armyId", "routes", "gridStr", "userId", "serverName", "userStates", "armyState")
    MAPID_FIELD_NUMBER: _ClassVar[int]
    ARMYID_FIELD_NUMBER: _ClassVar[int]
    ROUTES_FIELD_NUMBER: _ClassVar[int]
    GRIDSTR_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    USERSTATES_FIELD_NUMBER: _ClassVar[int]
    ARMYSTATE_FIELD_NUMBER: _ClassVar[int]
    mapId: int
    armyId: int
    routes: _containers.RepeatedCompositeFieldContainer[RouteMsg]
    gridStr: str
    userId: _containers.RepeatedScalarFieldContainer[int]
    serverName: str
    userStates: _containers.RepeatedCompositeFieldContainer[RouteStateMsg]
    armyState: int
    def __init__(self, mapId: _Optional[int] = ..., armyId: _Optional[int] = ..., routes: _Optional[_Iterable[_Union[RouteMsg, _Mapping]]] = ..., gridStr: _Optional[str] = ..., userId: _Optional[_Iterable[int]] = ..., serverName: _Optional[str] = ..., userStates: _Optional[_Iterable[_Union[RouteStateMsg, _Mapping]]] = ..., armyState: _Optional[int] = ...) -> None: ...

class PosMsg(_message.Message):
    __slots__ = ("x", "y")
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    x: int
    y: int
    def __init__(self, x: _Optional[int] = ..., y: _Optional[int] = ...) -> None: ...

class PowCardBufListMsg(_message.Message):
    __slots__ = ("bufInfos",)
    BUFINFOS_FIELD_NUMBER: _ClassVar[int]
    bufInfos: _containers.RepeatedCompositeFieldContainer[PowCardBufMsg]
    def __init__(self, bufInfos: _Optional[_Iterable[_Union[PowCardBufMsg, _Mapping]]] = ...) -> None: ...

class PowCardBufMsg(_message.Message):
    __slots__ = ("sonType", "bufId", "fixValue", "percent")
    SONTYPE_FIELD_NUMBER: _ClassVar[int]
    BUFID_FIELD_NUMBER: _ClassVar[int]
    FIXVALUE_FIELD_NUMBER: _ClassVar[int]
    PERCENT_FIELD_NUMBER: _ClassVar[int]
    sonType: int
    bufId: int
    fixValue: int
    percent: int
    def __init__(self, sonType: _Optional[int] = ..., bufId: _Optional[int] = ..., fixValue: _Optional[int] = ..., percent: _Optional[int] = ...) -> None: ...

class PowCardInfoMsg(_message.Message):
    __slots__ = ("tempId", "grade", "gp", "buf", "isActive")
    TEMPID_FIELD_NUMBER: _ClassVar[int]
    GRADE_FIELD_NUMBER: _ClassVar[int]
    GP_FIELD_NUMBER: _ClassVar[int]
    BUF_FIELD_NUMBER: _ClassVar[int]
    ISACTIVE_FIELD_NUMBER: _ClassVar[int]
    tempId: int
    grade: int
    gp: int
    buf: PowCardBufMsg
    isActive: int
    def __init__(self, tempId: _Optional[int] = ..., grade: _Optional[int] = ..., gp: _Optional[int] = ..., buf: _Optional[_Union[PowCardBufMsg, _Mapping]] = ..., isActive: _Optional[int] = ...) -> None: ...

class PowCardReqMsg(_message.Message):
    __slots__ = ("op", "cardId")
    OP_FIELD_NUMBER: _ClassVar[int]
    CARDID_FIELD_NUMBER: _ClassVar[int]
    op: int
    cardId: int
    def __init__(self, op: _Optional[int] = ..., cardId: _Optional[int] = ...) -> None: ...

class PowCardSuiteListMsg(_message.Message):
    __slots__ = ("suites",)
    SUITES_FIELD_NUMBER: _ClassVar[int]
    suites: _containers.RepeatedCompositeFieldContainer[PowCardSuiteMsg]
    def __init__(self, suites: _Optional[_Iterable[_Union[PowCardSuiteMsg, _Mapping]]] = ...) -> None: ...

class PowCardSuiteMsg(_message.Message):
    __slots__ = ("suiteId", "bufInfos", "cardInfos")
    SUITEID_FIELD_NUMBER: _ClassVar[int]
    BUFINFOS_FIELD_NUMBER: _ClassVar[int]
    CARDINFOS_FIELD_NUMBER: _ClassVar[int]
    suiteId: int
    bufInfos: _containers.RepeatedCompositeFieldContainer[PowCardBufMsg]
    cardInfos: _containers.RepeatedCompositeFieldContainer[PowCardInfoMsg]
    def __init__(self, suiteId: _Optional[int] = ..., bufInfos: _Optional[_Iterable[_Union[PowCardBufMsg, _Mapping]]] = ..., cardInfos: _Optional[_Iterable[_Union[PowCardInfoMsg, _Mapping]]] = ...) -> None: ...

class PowcardFightAddMsg(_message.Message):
    __slots__ = ("singlefightadd",)
    SINGLEFIGHTADD_FIELD_NUMBER: _ClassVar[int]
    singlefightadd: _containers.RepeatedCompositeFieldContainer[Singlefightadd]
    def __init__(self, singlefightadd: _Optional[_Iterable[_Union[Singlefightadd, _Mapping]]] = ...) -> None: ...

class PreLoadResMsg(_message.Message):
    __slots__ = ("armyId", "heroSkill", "soldierTempId", "soldierSkill")
    ARMYID_FIELD_NUMBER: _ClassVar[int]
    HEROSKILL_FIELD_NUMBER: _ClassVar[int]
    SOLDIERTEMPID_FIELD_NUMBER: _ClassVar[int]
    SOLDIERSKILL_FIELD_NUMBER: _ClassVar[int]
    armyId: int
    heroSkill: _containers.RepeatedScalarFieldContainer[int]
    soldierTempId: _containers.RepeatedScalarFieldContainer[int]
    soldierSkill: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, armyId: _Optional[int] = ..., heroSkill: _Optional[_Iterable[int]] = ..., soldierTempId: _Optional[_Iterable[int]] = ..., soldierSkill: _Optional[_Iterable[int]] = ...) -> None: ...

class PrepareOverLivingMsg(_message.Message):
    __slots__ = ("calcType", "livingId", "sp")
    CALCTYPE_FIELD_NUMBER: _ClassVar[int]
    LIVINGID_FIELD_NUMBER: _ClassVar[int]
    SP_FIELD_NUMBER: _ClassVar[int]
    calcType: int
    livingId: int
    sp: int
    def __init__(self, calcType: _Optional[int] = ..., livingId: _Optional[int] = ..., sp: _Optional[int] = ...) -> None: ...

class PrepareOverMsg(_message.Message):
    __slots__ = ("frame", "prepareOverLivings")
    FRAME_FIELD_NUMBER: _ClassVar[int]
    PREPAREOVERLIVINGS_FIELD_NUMBER: _ClassVar[int]
    frame: int
    prepareOverLivings: _containers.RepeatedCompositeFieldContainer[PrepareOverLivingMsg]
    def __init__(self, frame: _Optional[int] = ..., prepareOverLivings: _Optional[_Iterable[_Union[PrepareOverLivingMsg, _Mapping]]] = ...) -> None: ...

class PrivilegeMsg(_message.Message):
    __slots__ = ("isPrivilege", "list", "userName", "index", "param1", "param2")
    ISPRIVILEGE_FIELD_NUMBER: _ClassVar[int]
    LIST_FIELD_NUMBER: _ClassVar[int]
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    INDEX_FIELD_NUMBER: _ClassVar[int]
    PARAM1_FIELD_NUMBER: _ClassVar[int]
    PARAM2_FIELD_NUMBER: _ClassVar[int]
    isPrivilege: bool
    list: _containers.RepeatedScalarFieldContainer[int]
    userName: str
    index: int
    param1: str
    param2: str
    def __init__(self, isPrivilege: _Optional[bool] = ..., list: _Optional[_Iterable[int]] = ..., userName: _Optional[str] = ..., index: _Optional[int] = ..., param1: _Optional[str] = ..., param2: _Optional[str] = ...) -> None: ...

class PropertyUpdatedMsg(_message.Message):
    __slots__ = ("propertyType", "value")
    PROPERTYTYPE_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    propertyType: int
    value: int
    def __init__(self, propertyType: _Optional[int] = ..., value: _Optional[int] = ...) -> None: ...

class QteMsg(_message.Message):
    __slots__ = ("battleId", "serverName")
    BATTLEID_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    battleId: str
    serverName: str
    def __init__(self, battleId: _Optional[str] = ..., serverName: _Optional[str] = ...) -> None: ...

class QueryCollectCampaignNodeRspMsg(_message.Message):
    __slots__ = ("collectCampaignNode",)
    COLLECTCAMPAIGNNODE_FIELD_NUMBER: _ClassVar[int]
    collectCampaignNode: _containers.RepeatedCompositeFieldContainer[CollectCampaignNodeMsg]
    def __init__(self, collectCampaignNode: _Optional[_Iterable[_Union[CollectCampaignNodeMsg, _Mapping]]] = ...) -> None: ...

class QuestAddedMsg(_message.Message):
    __slots__ = ("questId",)
    QUESTID_FIELD_NUMBER: _ClassVar[int]
    questId: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, questId: _Optional[_Iterable[int]] = ...) -> None: ...

class QuestFinishedReqMsg(_message.Message):
    __slots__ = ("templateId", "rewardItemId", "isPass")
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    REWARDITEMID_FIELD_NUMBER: _ClassVar[int]
    ISPASS_FIELD_NUMBER: _ClassVar[int]
    templateId: int
    rewardItemId: int
    isPass: bool
    def __init__(self, templateId: _Optional[int] = ..., rewardItemId: _Optional[int] = ..., isPass: _Optional[bool] = ...) -> None: ...

class QuestFinishedRspMsg(_message.Message):
    __slots__ = ("templateId",)
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    templateId: int
    def __init__(self, templateId: _Optional[int] = ...) -> None: ...

class QuestInfo(_message.Message):
    __slots__ = ("templateId", "isComplete", "condition_1", "condition_2", "condition_3", "condition_4", "completedDate", "repeatFinish", "isAccept", "isSelect", "addDate")
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    ISCOMPLETE_FIELD_NUMBER: _ClassVar[int]
    CONDITION_1_FIELD_NUMBER: _ClassVar[int]
    CONDITION_2_FIELD_NUMBER: _ClassVar[int]
    CONDITION_3_FIELD_NUMBER: _ClassVar[int]
    CONDITION_4_FIELD_NUMBER: _ClassVar[int]
    COMPLETEDDATE_FIELD_NUMBER: _ClassVar[int]
    REPEATFINISH_FIELD_NUMBER: _ClassVar[int]
    ISACCEPT_FIELD_NUMBER: _ClassVar[int]
    ISSELECT_FIELD_NUMBER: _ClassVar[int]
    ADDDATE_FIELD_NUMBER: _ClassVar[int]
    templateId: int
    isComplete: bool
    condition_1: int
    condition_2: int
    condition_3: int
    condition_4: int
    completedDate: str
    repeatFinish: int
    isAccept: bool
    isSelect: bool
    addDate: str
    def __init__(self, templateId: _Optional[int] = ..., isComplete: _Optional[bool] = ..., condition_1: _Optional[int] = ..., condition_2: _Optional[int] = ..., condition_3: _Optional[int] = ..., condition_4: _Optional[int] = ..., completedDate: _Optional[str] = ..., repeatFinish: _Optional[int] = ..., isAccept: _Optional[bool] = ..., isSelect: _Optional[bool] = ..., addDate: _Optional[str] = ...) -> None: ...

class QuestRemovedMsg(_message.Message):
    __slots__ = ("templateId",)
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    templateId: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, templateId: _Optional[_Iterable[int]] = ...) -> None: ...

class QuestUpdatedRspMsg(_message.Message):
    __slots__ = ("quest", "statesLength", "states")
    QUEST_FIELD_NUMBER: _ClassVar[int]
    STATESLENGTH_FIELD_NUMBER: _ClassVar[int]
    STATES_FIELD_NUMBER: _ClassVar[int]
    quest: _containers.RepeatedCompositeFieldContainer[QuestInfo]
    statesLength: int
    states: bytes
    def __init__(self, quest: _Optional[_Iterable[_Union[QuestInfo, _Mapping]]] = ..., statesLength: _Optional[int] = ..., states: _Optional[bytes] = ...) -> None: ...

class QuestionDataRspInfo(_message.Message):
    __slots__ = ("questId", "answer")
    QUESTID_FIELD_NUMBER: _ClassVar[int]
    ANSWER_FIELD_NUMBER: _ClassVar[int]
    questId: int
    answer: str
    def __init__(self, questId: _Optional[int] = ..., answer: _Optional[str] = ...) -> None: ...

class QuestionDataRspMsg(_message.Message):
    __slots__ = ("isFirst", "id", "infolist")
    ISFIRST_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    INFOLIST_FIELD_NUMBER: _ClassVar[int]
    isFirst: int
    id: int
    infolist: _containers.RepeatedCompositeFieldContainer[QuestionDataRspInfo]
    def __init__(self, isFirst: _Optional[int] = ..., id: _Optional[int] = ..., infolist: _Optional[_Iterable[_Union[QuestionDataRspInfo, _Mapping]]] = ...) -> None: ...

class QuestionInfoMsg(_message.Message):
    __slots__ = ("id", "title", "type", "contenType", "a", "b", "c", "d", "e", "f", "g", "h", "i", "j")
    ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    CONTENTYPE_FIELD_NUMBER: _ClassVar[int]
    A_FIELD_NUMBER: _ClassVar[int]
    B_FIELD_NUMBER: _ClassVar[int]
    C_FIELD_NUMBER: _ClassVar[int]
    D_FIELD_NUMBER: _ClassVar[int]
    E_FIELD_NUMBER: _ClassVar[int]
    F_FIELD_NUMBER: _ClassVar[int]
    G_FIELD_NUMBER: _ClassVar[int]
    H_FIELD_NUMBER: _ClassVar[int]
    I_FIELD_NUMBER: _ClassVar[int]
    J_FIELD_NUMBER: _ClassVar[int]
    id: int
    title: str
    type: int
    contenType: int
    a: str
    b: str
    c: str
    d: str
    e: str
    f: str
    g: str
    h: str
    i: str
    j: str
    def __init__(self, id: _Optional[int] = ..., title: _Optional[str] = ..., type: _Optional[int] = ..., contenType: _Optional[int] = ..., a: _Optional[str] = ..., b: _Optional[str] = ..., c: _Optional[str] = ..., d: _Optional[str] = ..., e: _Optional[str] = ..., f: _Optional[str] = ..., g: _Optional[str] = ..., h: _Optional[str] = ..., i: _Optional[str] = ..., j: _Optional[str] = ...) -> None: ...

class QuestionReplayMsg(_message.Message):
    __slots__ = ("questionId", "type", "userId", "title", "content", "replayContent", "commitTime", "replayUserName", "employ", "stopReply")
    QUESTIONID_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    REPLAYCONTENT_FIELD_NUMBER: _ClassVar[int]
    COMMITTIME_FIELD_NUMBER: _ClassVar[int]
    REPLAYUSERNAME_FIELD_NUMBER: _ClassVar[int]
    EMPLOY_FIELD_NUMBER: _ClassVar[int]
    STOPREPLY_FIELD_NUMBER: _ClassVar[int]
    questionId: str
    type: int
    userId: int
    title: str
    content: str
    replayContent: str
    commitTime: bytes
    replayUserName: str
    employ: int
    stopReply: int
    def __init__(self, questionId: _Optional[str] = ..., type: _Optional[int] = ..., userId: _Optional[int] = ..., title: _Optional[str] = ..., content: _Optional[str] = ..., replayContent: _Optional[str] = ..., commitTime: _Optional[bytes] = ..., replayUserName: _Optional[str] = ..., employ: _Optional[int] = ..., stopReply: _Optional[int] = ...) -> None: ...

class QuestionnarieInfoMsg(_message.Message):
    __slots__ = ("id", "title", "content", "itemId1", "count1", "itemId2", "count2", "itemId3", "count3", "itemId4", "count4", "questiones")
    ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    ITEMID1_FIELD_NUMBER: _ClassVar[int]
    COUNT1_FIELD_NUMBER: _ClassVar[int]
    ITEMID2_FIELD_NUMBER: _ClassVar[int]
    COUNT2_FIELD_NUMBER: _ClassVar[int]
    ITEMID3_FIELD_NUMBER: _ClassVar[int]
    COUNT3_FIELD_NUMBER: _ClassVar[int]
    ITEMID4_FIELD_NUMBER: _ClassVar[int]
    COUNT4_FIELD_NUMBER: _ClassVar[int]
    QUESTIONES_FIELD_NUMBER: _ClassVar[int]
    id: int
    title: str
    content: str
    itemId1: int
    count1: int
    itemId2: int
    count2: int
    itemId3: int
    count3: int
    itemId4: int
    count4: int
    questiones: _containers.RepeatedCompositeFieldContainer[QuestionInfoMsg]
    def __init__(self, id: _Optional[int] = ..., title: _Optional[str] = ..., content: _Optional[str] = ..., itemId1: _Optional[int] = ..., count1: _Optional[int] = ..., itemId2: _Optional[int] = ..., count2: _Optional[int] = ..., itemId3: _Optional[int] = ..., count3: _Optional[int] = ..., itemId4: _Optional[int] = ..., count4: _Optional[int] = ..., questiones: _Optional[_Iterable[_Union[QuestionInfoMsg, _Mapping]]] = ...) -> None: ...

class QuickHangupMsg(_message.Message):
    __slots__ = ("quickTime", "payType")
    QUICKTIME_FIELD_NUMBER: _ClassVar[int]
    PAYTYPE_FIELD_NUMBER: _ClassVar[int]
    quickTime: int
    payType: int
    def __init__(self, quickTime: _Optional[int] = ..., payType: _Optional[int] = ...) -> None: ...

class RankInfoMsg(_message.Message):
    __slots__ = ("index", "rank")
    INDEX_FIELD_NUMBER: _ClassVar[int]
    RANK_FIELD_NUMBER: _ClassVar[int]
    index: int
    rank: int
    def __init__(self, index: _Optional[int] = ..., rank: _Optional[int] = ...) -> None: ...

class RankListRspMsg(_message.Message):
    __slots__ = ("rankInfo",)
    RANKINFO_FIELD_NUMBER: _ClassVar[int]
    rankInfo: _containers.RepeatedCompositeFieldContainer[RankMsg]
    def __init__(self, rankInfo: _Optional[_Iterable[_Union[RankMsg, _Mapping]]] = ...) -> None: ...

class RankMsg(_message.Message):
    __slots__ = ("userId", "campaignId", "rank")
    USERID_FIELD_NUMBER: _ClassVar[int]
    CAMPAIGNID_FIELD_NUMBER: _ClassVar[int]
    RANK_FIELD_NUMBER: _ClassVar[int]
    userId: int
    campaignId: int
    rank: int
    def __init__(self, userId: _Optional[int] = ..., campaignId: _Optional[int] = ..., rank: _Optional[int] = ...) -> None: ...

class RankRewardMsg(_message.Message):
    __slots__ = ("type", "status", "rank", "opType")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    RANK_FIELD_NUMBER: _ClassVar[int]
    OPTYPE_FIELD_NUMBER: _ClassVar[int]
    type: int
    status: int
    rank: int
    opType: int
    def __init__(self, type: _Optional[int] = ..., status: _Optional[int] = ..., rank: _Optional[int] = ..., opType: _Optional[int] = ...) -> None: ...

class RateUpdate(_message.Message):
    __slots__ = ("rate", "beginTime", "endTime", "beginDay", "endDay", "bufferType", "param1", "param2", "rateName", "rateDesc")
    RATE_FIELD_NUMBER: _ClassVar[int]
    BEGINTIME_FIELD_NUMBER: _ClassVar[int]
    ENDTIME_FIELD_NUMBER: _ClassVar[int]
    BEGINDAY_FIELD_NUMBER: _ClassVar[int]
    ENDDAY_FIELD_NUMBER: _ClassVar[int]
    BUFFERTYPE_FIELD_NUMBER: _ClassVar[int]
    PARAM1_FIELD_NUMBER: _ClassVar[int]
    PARAM2_FIELD_NUMBER: _ClassVar[int]
    RATENAME_FIELD_NUMBER: _ClassVar[int]
    RATEDESC_FIELD_NUMBER: _ClassVar[int]
    rate: int
    beginTime: int
    endTime: int
    beginDay: str
    endDay: str
    bufferType: int
    param1: str
    param2: str
    rateName: str
    rateDesc: str
    def __init__(self, rate: _Optional[int] = ..., beginTime: _Optional[int] = ..., endTime: _Optional[int] = ..., beginDay: _Optional[str] = ..., endDay: _Optional[str] = ..., bufferType: _Optional[int] = ..., param1: _Optional[str] = ..., param2: _Optional[str] = ..., rateName: _Optional[str] = ..., rateDesc: _Optional[str] = ...) -> None: ...

class RateUpdateReqMsg(_message.Message):
    __slots__ = ("rateInfo",)
    RATEINFO_FIELD_NUMBER: _ClassVar[int]
    rateInfo: _containers.RepeatedCompositeFieldContainer[RateUpdate]
    def __init__(self, rateInfo: _Optional[_Iterable[_Union[RateUpdate, _Mapping]]] = ...) -> None: ...

class RebateInfoMsg(_message.Message):
    __slots__ = ("id", "beginDate", "endDate", "type", "packages")
    ID_FIELD_NUMBER: _ClassVar[int]
    BEGINDATE_FIELD_NUMBER: _ClassVar[int]
    ENDDATE_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    PACKAGES_FIELD_NUMBER: _ClassVar[int]
    id: str
    beginDate: str
    endDate: str
    type: int
    packages: _containers.RepeatedCompositeFieldContainer[PackageInfoMsg]
    def __init__(self, id: _Optional[str] = ..., beginDate: _Optional[str] = ..., endDate: _Optional[str] = ..., type: _Optional[int] = ..., packages: _Optional[_Iterable[_Union[PackageInfoMsg, _Mapping]]] = ...) -> None: ...

class RebateOpMsg(_message.Message):
    __slots__ = ("id", "packageid", "op")
    ID_FIELD_NUMBER: _ClassVar[int]
    PACKAGEID_FIELD_NUMBER: _ClassVar[int]
    OP_FIELD_NUMBER: _ClassVar[int]
    id: str
    packageid: str
    op: int
    def __init__(self, id: _Optional[str] = ..., packageid: _Optional[str] = ..., op: _Optional[int] = ...) -> None: ...

class ReceiveMailMsg(_message.Message):
    __slots__ = ("mailInfos",)
    MAILINFOS_FIELD_NUMBER: _ClassVar[int]
    mailInfos: _containers.RepeatedCompositeFieldContainer[MailInfoMsg]
    def __init__(self, mailInfos: _Optional[_Iterable[_Union[MailInfoMsg, _Mapping]]] = ...) -> None: ...

class RecentContractsStateReqMsg(_message.Message):
    __slots__ = ("userId",)
    USERID_FIELD_NUMBER: _ClassVar[int]
    userId: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, userId: _Optional[_Iterable[int]] = ...) -> None: ...

class RecommendListMsg(_message.Message):
    __slots__ = ("girlList", "boyList")
    GIRLLIST_FIELD_NUMBER: _ClassVar[int]
    BOYLIST_FIELD_NUMBER: _ClassVar[int]
    girlList: _containers.RepeatedCompositeFieldContainer[FriendPlayer]
    boyList: _containers.RepeatedCompositeFieldContainer[FriendPlayer]
    def __init__(self, girlList: _Optional[_Iterable[_Union[FriendPlayer, _Mapping]]] = ..., boyList: _Optional[_Iterable[_Union[FriendPlayer, _Mapping]]] = ...) -> None: ...

class RecoverInfo(_message.Message):
    __slots__ = ("sonType", "num", "itemCost", "itemReward", "goldCost", "goldReward")
    SONTYPE_FIELD_NUMBER: _ClassVar[int]
    NUM_FIELD_NUMBER: _ClassVar[int]
    ITEMCOST_FIELD_NUMBER: _ClassVar[int]
    ITEMREWARD_FIELD_NUMBER: _ClassVar[int]
    GOLDCOST_FIELD_NUMBER: _ClassVar[int]
    GOLDREWARD_FIELD_NUMBER: _ClassVar[int]
    sonType: int
    num: int
    itemCost: int
    itemReward: int
    goldCost: int
    goldReward: int
    def __init__(self, sonType: _Optional[int] = ..., num: _Optional[int] = ..., itemCost: _Optional[int] = ..., itemReward: _Optional[int] = ..., goldCost: _Optional[int] = ..., goldReward: _Optional[int] = ...) -> None: ...

class RecoverInfosMsg(_message.Message):
    __slots__ = ("recoverInfos",)
    RECOVERINFOS_FIELD_NUMBER: _ClassVar[int]
    recoverInfos: _containers.RepeatedCompositeFieldContainer[RecoverInfo]
    def __init__(self, recoverInfos: _Optional[_Iterable[_Union[RecoverInfo, _Mapping]]] = ...) -> None: ...

class RecoverReqMsg(_message.Message):
    __slots__ = ("type", "count", "way")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    WAY_FIELD_NUMBER: _ClassVar[int]
    type: int
    count: int
    way: int
    def __init__(self, type: _Optional[int] = ..., count: _Optional[int] = ..., way: _Optional[int] = ...) -> None: ...

class RefreshPropertyRepMsg(_message.Message):
    __slots__ = ("randomSkill", "lockPos", "result")
    RANDOMSKILL_FIELD_NUMBER: _ClassVar[int]
    LOCKPOS_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    randomSkill: _containers.RepeatedScalarFieldContainer[int]
    lockPos: _containers.RepeatedScalarFieldContainer[bool]
    result: int
    def __init__(self, randomSkill: _Optional[_Iterable[int]] = ..., lockPos: _Optional[_Iterable[bool]] = ..., result: _Optional[int] = ...) -> None: ...

class RefreshPropertyReqMsg(_message.Message):
    __slots__ = ("itemId",)
    ITEMID_FIELD_NUMBER: _ClassVar[int]
    itemId: int
    def __init__(self, itemId: _Optional[int] = ...) -> None: ...

class RefuseFriendRspMsg(_message.Message):
    __slots__ = ("result",)
    RESULT_FIELD_NUMBER: _ClassVar[int]
    result: bool
    def __init__(self, result: _Optional[bool] = ...) -> None: ...

class ReinforceMsg(_message.Message):
    __slots__ = ("side", "hero", "soldiers", "reinforceWave", "pets")
    SIDE_FIELD_NUMBER: _ClassVar[int]
    HERO_FIELD_NUMBER: _ClassVar[int]
    SOLDIERS_FIELD_NUMBER: _ClassVar[int]
    REINFORCEWAVE_FIELD_NUMBER: _ClassVar[int]
    PETS_FIELD_NUMBER: _ClassVar[int]
    side: int
    hero: _containers.RepeatedCompositeFieldContainer[HeroMsg]
    soldiers: _containers.RepeatedCompositeFieldContainer[SoldierMsg]
    reinforceWave: int
    pets: _containers.RepeatedCompositeFieldContainer[HeroMsg]
    def __init__(self, side: _Optional[int] = ..., hero: _Optional[_Iterable[_Union[HeroMsg, _Mapping]]] = ..., soldiers: _Optional[_Iterable[_Union[SoldierMsg, _Mapping]]] = ..., reinforceWave: _Optional[int] = ..., pets: _Optional[_Iterable[_Union[HeroMsg, _Mapping]]] = ...) -> None: ...

class RelationPlayerMsg(_message.Message):
    __slots__ = ("relation", "friendRp", "friendGrade", "groupId", "player", "snsInfo", "isVip")
    RELATION_FIELD_NUMBER: _ClassVar[int]
    FRIENDRP_FIELD_NUMBER: _ClassVar[int]
    FRIENDGRADE_FIELD_NUMBER: _ClassVar[int]
    GROUPID_FIELD_NUMBER: _ClassVar[int]
    PLAYER_FIELD_NUMBER: _ClassVar[int]
    SNSINFO_FIELD_NUMBER: _ClassVar[int]
    FROM_FIELD_NUMBER: _ClassVar[int]
    ISVIP_FIELD_NUMBER: _ClassVar[int]
    relation: int
    friendRp: int
    friendGrade: int
    groupId: int
    player: SimplePlayerInfoMsg
    snsInfo: SNSInfoMsg
    isVip: int
    def __init__(self, relation: _Optional[int] = ..., friendRp: _Optional[int] = ..., friendGrade: _Optional[int] = ..., groupId: _Optional[int] = ..., player: _Optional[_Union[SimplePlayerInfoMsg, _Mapping]] = ..., snsInfo: _Optional[_Union[SNSInfoMsg, _Mapping]] = ..., isVip: _Optional[int] = ..., **kwargs) -> None: ...

class RentalBagOpReqMsg(_message.Message):
    __slots__ = ("opType", "param1", "param2")
    OPTYPE_FIELD_NUMBER: _ClassVar[int]
    PARAM1_FIELD_NUMBER: _ClassVar[int]
    PARAM2_FIELD_NUMBER: _ClassVar[int]
    opType: int
    param1: int
    param2: str
    def __init__(self, opType: _Optional[int] = ..., param1: _Optional[int] = ..., param2: _Optional[str] = ...) -> None: ...

class RentalBagOpResMsg(_message.Message):
    __slots__ = ("opType", "rentalBagTime", "status", "param1")
    OPTYPE_FIELD_NUMBER: _ClassVar[int]
    RENTALBAGTIME_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    PARAM1_FIELD_NUMBER: _ClassVar[int]
    opType: int
    rentalBagTime: str
    status: int
    param1: str
    def __init__(self, opType: _Optional[int] = ..., rentalBagTime: _Optional[str] = ..., status: _Optional[int] = ..., param1: _Optional[str] = ...) -> None: ...

class ReplacementMsg(_message.Message):
    __slots__ = ("stateStr",)
    STATESTR_FIELD_NUMBER: _ClassVar[int]
    stateStr: str
    def __init__(self, stateStr: _Optional[str] = ...) -> None: ...

class ReplayListMsg(_message.Message):
    __slots__ = ("questionInfos",)
    QUESTIONINFOS_FIELD_NUMBER: _ClassVar[int]
    questionInfos: _containers.RepeatedCompositeFieldContainer[QuestionReplayMsg]
    def __init__(self, questionInfos: _Optional[_Iterable[_Union[QuestionReplayMsg, _Mapping]]] = ...) -> None: ...

class Result(_message.Message):
    __slots__ = ("fishId", "state", "tool")
    FISHID_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    TOOL_FIELD_NUMBER: _ClassVar[int]
    fishId: int
    state: int
    tool: int
    def __init__(self, fishId: _Optional[int] = ..., state: _Optional[int] = ..., tool: _Optional[int] = ...) -> None: ...

class ReturnOptionMsg(_message.Message):
    __slots__ = ("optionType", "param1")
    OPTIONTYPE_FIELD_NUMBER: _ClassVar[int]
    PARAM1_FIELD_NUMBER: _ClassVar[int]
    optionType: int
    param1: int
    def __init__(self, optionType: _Optional[int] = ..., param1: _Optional[int] = ...) -> None: ...

class RewardAddedMsg(_message.Message):
    __slots__ = ("rewardId",)
    REWARDID_FIELD_NUMBER: _ClassVar[int]
    rewardId: int
    def __init__(self, rewardId: _Optional[int] = ...) -> None: ...

class RewardArrestMsg(_message.Message):
    __slots__ = ("param1", "condictionType")
    PARAM1_FIELD_NUMBER: _ClassVar[int]
    CONDICTIONTYPE_FIELD_NUMBER: _ClassVar[int]
    param1: int
    condictionType: int
    def __init__(self, param1: _Optional[int] = ..., condictionType: _Optional[int] = ...) -> None: ...

class RewardCountUpdateRspMsg(_message.Message):
    __slots__ = ("rewardCount",)
    REWARDCOUNT_FIELD_NUMBER: _ClassVar[int]
    rewardCount: int
    def __init__(self, rewardCount: _Optional[int] = ...) -> None: ...

class RewardFinishedReqMsg(_message.Message):
    __slots__ = ("templateId", "rewardItemId", "isPass")
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    REWARDITEMID_FIELD_NUMBER: _ClassVar[int]
    ISPASS_FIELD_NUMBER: _ClassVar[int]
    templateId: int
    rewardItemId: int
    isPass: bool
    def __init__(self, templateId: _Optional[int] = ..., rewardItemId: _Optional[int] = ..., isPass: _Optional[bool] = ...) -> None: ...

class RewardFinishedRspMsg(_message.Message):
    __slots__ = ("templateId",)
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    templateId: int
    def __init__(self, templateId: _Optional[int] = ...) -> None: ...

class RewardFreshReqMsg(_message.Message):
    __slots__ = ("isButton", "payType")
    ISBUTTON_FIELD_NUMBER: _ClassVar[int]
    PAYTYPE_FIELD_NUMBER: _ClassVar[int]
    isButton: bool
    payType: int
    def __init__(self, isButton: _Optional[bool] = ..., payType: _Optional[int] = ...) -> None: ...

class RewardFreshRspMsg(_message.Message):
    __slots__ = ("templateId", "rewardLastdate", "isIsValid", "qualitys", "rewardTimes", "freeTimes")
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    REWARDLASTDATE_FIELD_NUMBER: _ClassVar[int]
    ISISVALID_FIELD_NUMBER: _ClassVar[int]
    QUALITYS_FIELD_NUMBER: _ClassVar[int]
    REWARDTIMES_FIELD_NUMBER: _ClassVar[int]
    FREETIMES_FIELD_NUMBER: _ClassVar[int]
    templateId: _containers.RepeatedScalarFieldContainer[int]
    rewardLastdate: str
    isIsValid: _containers.RepeatedScalarFieldContainer[int]
    qualitys: _containers.RepeatedScalarFieldContainer[int]
    rewardTimes: int
    freeTimes: int
    def __init__(self, templateId: _Optional[_Iterable[int]] = ..., rewardLastdate: _Optional[str] = ..., isIsValid: _Optional[_Iterable[int]] = ..., qualitys: _Optional[_Iterable[int]] = ..., rewardTimes: _Optional[int] = ..., freeTimes: _Optional[int] = ...) -> None: ...

class RewardInfo(_message.Message):
    __slots__ = ("templateId", "isComplete", "condition_1", "condition_2", "condition_3", "condition_4", "completedDate", "repeatFinish", "isAccept", "isSelect", "quality")
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    ISCOMPLETE_FIELD_NUMBER: _ClassVar[int]
    CONDITION_1_FIELD_NUMBER: _ClassVar[int]
    CONDITION_2_FIELD_NUMBER: _ClassVar[int]
    CONDITION_3_FIELD_NUMBER: _ClassVar[int]
    CONDITION_4_FIELD_NUMBER: _ClassVar[int]
    COMPLETEDDATE_FIELD_NUMBER: _ClassVar[int]
    REPEATFINISH_FIELD_NUMBER: _ClassVar[int]
    ISACCEPT_FIELD_NUMBER: _ClassVar[int]
    ISSELECT_FIELD_NUMBER: _ClassVar[int]
    QUALITY_FIELD_NUMBER: _ClassVar[int]
    templateId: int
    isComplete: bool
    condition_1: int
    condition_2: int
    condition_3: int
    condition_4: int
    completedDate: str
    repeatFinish: int
    isAccept: bool
    isSelect: bool
    quality: int
    def __init__(self, templateId: _Optional[int] = ..., isComplete: _Optional[bool] = ..., condition_1: _Optional[int] = ..., condition_2: _Optional[int] = ..., condition_3: _Optional[int] = ..., condition_4: _Optional[int] = ..., completedDate: _Optional[str] = ..., repeatFinish: _Optional[int] = ..., isAccept: _Optional[bool] = ..., isSelect: _Optional[bool] = ..., quality: _Optional[int] = ...) -> None: ...

class RewardInfoMsg(_message.Message):
    __slots__ = ("rewardId",)
    REWARDID_FIELD_NUMBER: _ClassVar[int]
    rewardId: int
    def __init__(self, rewardId: _Optional[int] = ...) -> None: ...

class RewardRemovedMsg(_message.Message):
    __slots__ = ("templateId",)
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    templateId: int
    def __init__(self, templateId: _Optional[int] = ...) -> None: ...

class RewardUpdatedRspMsg(_message.Message):
    __slots__ = ("reward", "statesLength", "states")
    REWARD_FIELD_NUMBER: _ClassVar[int]
    STATESLENGTH_FIELD_NUMBER: _ClassVar[int]
    STATES_FIELD_NUMBER: _ClassVar[int]
    reward: _containers.RepeatedCompositeFieldContainer[RewardInfo]
    statesLength: int
    states: bytes
    def __init__(self, reward: _Optional[_Iterable[_Union[RewardInfo, _Mapping]]] = ..., statesLength: _Optional[int] = ..., states: _Optional[bytes] = ...) -> None: ...

class RoomCreatedMsg(_message.Message):
    __slots__ = ("createdType", "room", "isCross")
    CREATEDTYPE_FIELD_NUMBER: _ClassVar[int]
    ROOM_FIELD_NUMBER: _ClassVar[int]
    ISCROSS_FIELD_NUMBER: _ClassVar[int]
    createdType: int
    room: RoomMsg
    isCross: bool
    def __init__(self, createdType: _Optional[int] = ..., room: _Optional[_Union[RoomMsg, _Mapping]] = ..., isCross: _Optional[bool] = ...) -> None: ...

class RoomEnterMsg(_message.Message):
    __slots__ = ("result", "player")
    RESULT_FIELD_NUMBER: _ClassVar[int]
    PLAYER_FIELD_NUMBER: _ClassVar[int]
    result: int
    player: _containers.RepeatedCompositeFieldContainer[RoomPlayerMsg]
    def __init__(self, result: _Optional[int] = ..., player: _Optional[_Iterable[_Union[RoomPlayerMsg, _Mapping]]] = ...) -> None: ...

class RoomExitMsg(_message.Message):
    __slots__ = ("msg",)
    MSG_FIELD_NUMBER: _ClassVar[int]
    msg: str
    def __init__(self, msg: _Optional[str] = ...) -> None: ...

class RoomExitRspMsg(_message.Message):
    __slots__ = ("playerId", "exitType", "param1")
    PLAYERID_FIELD_NUMBER: _ClassVar[int]
    EXITTYPE_FIELD_NUMBER: _ClassVar[int]
    PARAM1_FIELD_NUMBER: _ClassVar[int]
    playerId: int
    exitType: int
    param1: int
    def __init__(self, playerId: _Optional[int] = ..., exitType: _Optional[int] = ..., param1: _Optional[int] = ...) -> None: ...

class RoomInviteMsg(_message.Message):
    __slots__ = ("roomId", "playerId", "nickName", "name", "signStr", "roomType", "tempId", "position", "userKey", "bossCount", "isCross")
    ROOMID_FIELD_NUMBER: _ClassVar[int]
    PLAYERID_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    SIGNSTR_FIELD_NUMBER: _ClassVar[int]
    ROOMTYPE_FIELD_NUMBER: _ClassVar[int]
    TEMPID_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    USERKEY_FIELD_NUMBER: _ClassVar[int]
    BOSSCOUNT_FIELD_NUMBER: _ClassVar[int]
    ISCROSS_FIELD_NUMBER: _ClassVar[int]
    roomId: int
    playerId: int
    nickName: str
    name: str
    signStr: str
    roomType: int
    tempId: int
    position: int
    userKey: str
    bossCount: int
    isCross: bool
    def __init__(self, roomId: _Optional[int] = ..., playerId: _Optional[int] = ..., nickName: _Optional[str] = ..., name: _Optional[str] = ..., signStr: _Optional[str] = ..., roomType: _Optional[int] = ..., tempId: _Optional[int] = ..., position: _Optional[int] = ..., userKey: _Optional[str] = ..., bossCount: _Optional[int] = ..., isCross: _Optional[bool] = ...) -> None: ...

class RoomListRspMsg(_message.Message):
    __slots__ = ("room",)
    ROOM_FIELD_NUMBER: _ClassVar[int]
    room: _containers.RepeatedCompositeFieldContainer[RoomMsg]
    def __init__(self, room: _Optional[_Iterable[_Union[RoomMsg, _Mapping]]] = ...) -> None: ...

class RoomMsg(_message.Message):
    __slots__ = ("roomId", "campaignId", "masterId", "name", "count", "capacity", "roomState", "roomType", "isSetPassword")
    ROOMID_FIELD_NUMBER: _ClassVar[int]
    CAMPAIGNID_FIELD_NUMBER: _ClassVar[int]
    MASTERID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    CAPACITY_FIELD_NUMBER: _ClassVar[int]
    ROOMSTATE_FIELD_NUMBER: _ClassVar[int]
    ROOMTYPE_FIELD_NUMBER: _ClassVar[int]
    ISSETPASSWORD_FIELD_NUMBER: _ClassVar[int]
    roomId: int
    campaignId: int
    masterId: int
    name: str
    count: int
    capacity: int
    roomState: int
    roomType: int
    isSetPassword: bool
    def __init__(self, roomId: _Optional[int] = ..., campaignId: _Optional[int] = ..., masterId: _Optional[int] = ..., name: _Optional[str] = ..., count: _Optional[int] = ..., capacity: _Optional[int] = ..., roomState: _Optional[int] = ..., roomType: _Optional[int] = ..., isSetPassword: _Optional[bool] = ...) -> None: ...

class RoomPlayerListMsg(_message.Message):
    __slots__ = ("state", "roomPlayer")
    STATE_FIELD_NUMBER: _ClassVar[int]
    ROOMPLAYER_FIELD_NUMBER: _ClassVar[int]
    state: int
    roomPlayer: _containers.RepeatedCompositeFieldContainer[RoomPlayerMsg]
    def __init__(self, state: _Optional[int] = ..., roomPlayer: _Optional[_Iterable[_Union[RoomPlayerMsg, _Mapping]]] = ...) -> None: ...

class RoomPlayerMsg(_message.Message):
    __slots__ = ("roomId", "count", "currentRoomIndex", "playerState", "heroId", "playerId", "grades", "nickName", "sex", "templateId", "arm", "cloth", "armyId", "fightingCapacity", "curPosX", "curPosY", "campaignId", "onlineState", "consortiaId", "consortiaName", "changeShapeId", "armyState", "teamId", "bufferTempId", "geste", "headId", "isVip", "vipType", "mountTempId", "mountGrade", "wing", "serverName", "hat", "fashionArm", "fashionCloth", "hide", "appellid", "vehicleTemplateId", "fateSkills", "petTemplateId", "petQuqlity", "petName", "isNoGet", "dragonGrade", "transferGrade")
    ROOMID_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    CURRENTROOMINDEX_FIELD_NUMBER: _ClassVar[int]
    PLAYERSTATE_FIELD_NUMBER: _ClassVar[int]
    HEROID_FIELD_NUMBER: _ClassVar[int]
    PLAYERID_FIELD_NUMBER: _ClassVar[int]
    GRADES_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    SEX_FIELD_NUMBER: _ClassVar[int]
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    ARM_FIELD_NUMBER: _ClassVar[int]
    CLOTH_FIELD_NUMBER: _ClassVar[int]
    ARMYID_FIELD_NUMBER: _ClassVar[int]
    FIGHTINGCAPACITY_FIELD_NUMBER: _ClassVar[int]
    CURPOSX_FIELD_NUMBER: _ClassVar[int]
    CURPOSY_FIELD_NUMBER: _ClassVar[int]
    CAMPAIGNID_FIELD_NUMBER: _ClassVar[int]
    ONLINESTATE_FIELD_NUMBER: _ClassVar[int]
    CONSORTIAID_FIELD_NUMBER: _ClassVar[int]
    CONSORTIANAME_FIELD_NUMBER: _ClassVar[int]
    CHANGESHAPEID_FIELD_NUMBER: _ClassVar[int]
    ARMYSTATE_FIELD_NUMBER: _ClassVar[int]
    TEAMID_FIELD_NUMBER: _ClassVar[int]
    BUFFERTEMPID_FIELD_NUMBER: _ClassVar[int]
    GESTE_FIELD_NUMBER: _ClassVar[int]
    HEADID_FIELD_NUMBER: _ClassVar[int]
    ISVIP_FIELD_NUMBER: _ClassVar[int]
    VIPTYPE_FIELD_NUMBER: _ClassVar[int]
    MOUNTTEMPID_FIELD_NUMBER: _ClassVar[int]
    MOUNTGRADE_FIELD_NUMBER: _ClassVar[int]
    WING_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    HAT_FIELD_NUMBER: _ClassVar[int]
    FASHIONARM_FIELD_NUMBER: _ClassVar[int]
    FASHIONCLOTH_FIELD_NUMBER: _ClassVar[int]
    HIDE_FIELD_NUMBER: _ClassVar[int]
    APPELLID_FIELD_NUMBER: _ClassVar[int]
    VEHICLETEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    FATESKILLS_FIELD_NUMBER: _ClassVar[int]
    PETTEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    PETQUQLITY_FIELD_NUMBER: _ClassVar[int]
    PETNAME_FIELD_NUMBER: _ClassVar[int]
    ISNOGET_FIELD_NUMBER: _ClassVar[int]
    DRAGONGRADE_FIELD_NUMBER: _ClassVar[int]
    TRANSFERGRADE_FIELD_NUMBER: _ClassVar[int]
    roomId: int
    count: int
    currentRoomIndex: int
    playerState: int
    heroId: int
    playerId: int
    grades: int
    nickName: str
    sex: int
    templateId: int
    arm: str
    cloth: str
    armyId: int
    fightingCapacity: int
    curPosX: int
    curPosY: int
    campaignId: int
    onlineState: bool
    consortiaId: int
    consortiaName: str
    changeShapeId: int
    armyState: int
    teamId: int
    bufferTempId: int
    geste: int
    headId: int
    isVip: bool
    vipType: int
    mountTempId: int
    mountGrade: int
    wing: str
    serverName: str
    hat: str
    fashionArm: str
    fashionCloth: str
    hide: bool
    appellid: int
    vehicleTemplateId: int
    fateSkills: str
    petTemplateId: int
    petQuqlity: int
    petName: str
    isNoGet: bool
    dragonGrade: str
    transferGrade: int
    def __init__(self, roomId: _Optional[int] = ..., count: _Optional[int] = ..., currentRoomIndex: _Optional[int] = ..., playerState: _Optional[int] = ..., heroId: _Optional[int] = ..., playerId: _Optional[int] = ..., grades: _Optional[int] = ..., nickName: _Optional[str] = ..., sex: _Optional[int] = ..., templateId: _Optional[int] = ..., arm: _Optional[str] = ..., cloth: _Optional[str] = ..., armyId: _Optional[int] = ..., fightingCapacity: _Optional[int] = ..., curPosX: _Optional[int] = ..., curPosY: _Optional[int] = ..., campaignId: _Optional[int] = ..., onlineState: _Optional[bool] = ..., consortiaId: _Optional[int] = ..., consortiaName: _Optional[str] = ..., changeShapeId: _Optional[int] = ..., armyState: _Optional[int] = ..., teamId: _Optional[int] = ..., bufferTempId: _Optional[int] = ..., geste: _Optional[int] = ..., headId: _Optional[int] = ..., isVip: _Optional[bool] = ..., vipType: _Optional[int] = ..., mountTempId: _Optional[int] = ..., mountGrade: _Optional[int] = ..., wing: _Optional[str] = ..., serverName: _Optional[str] = ..., hat: _Optional[str] = ..., fashionArm: _Optional[str] = ..., fashionCloth: _Optional[str] = ..., hide: _Optional[bool] = ..., appellid: _Optional[int] = ..., vehicleTemplateId: _Optional[int] = ..., fateSkills: _Optional[str] = ..., petTemplateId: _Optional[int] = ..., petQuqlity: _Optional[int] = ..., petName: _Optional[str] = ..., isNoGet: _Optional[bool] = ..., dragonGrade: _Optional[str] = ..., transferGrade: _Optional[int] = ...) -> None: ...

class RoomPlayerReady(_message.Message):
    __slots__ = ("playerId", "readyState")
    PLAYERID_FIELD_NUMBER: _ClassVar[int]
    READYSTATE_FIELD_NUMBER: _ClassVar[int]
    playerId: int
    readyState: int
    def __init__(self, playerId: _Optional[int] = ..., readyState: _Optional[int] = ...) -> None: ...

class RoomReqMsg(_message.Message):
    __slots__ = ("roomId", "dungeonId", "campaignId", "armyId", "userId", "state", "index", "open", "roomType", "nameKey", "password", "isInvite", "capacity", "isGet")
    ROOMID_FIELD_NUMBER: _ClassVar[int]
    DUNGEONID_FIELD_NUMBER: _ClassVar[int]
    CAMPAIGNID_FIELD_NUMBER: _ClassVar[int]
    ARMYID_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    INDEX_FIELD_NUMBER: _ClassVar[int]
    OPEN_FIELD_NUMBER: _ClassVar[int]
    ROOMTYPE_FIELD_NUMBER: _ClassVar[int]
    NAMEKEY_FIELD_NUMBER: _ClassVar[int]
    PASSWORD_FIELD_NUMBER: _ClassVar[int]
    ISINVITE_FIELD_NUMBER: _ClassVar[int]
    CAPACITY_FIELD_NUMBER: _ClassVar[int]
    ISGET_FIELD_NUMBER: _ClassVar[int]
    roomId: int
    dungeonId: int
    campaignId: int
    armyId: int
    userId: int
    state: int
    index: int
    open: bool
    roomType: int
    nameKey: str
    password: str
    isInvite: bool
    capacity: int
    isGet: bool
    def __init__(self, roomId: _Optional[int] = ..., dungeonId: _Optional[int] = ..., campaignId: _Optional[int] = ..., armyId: _Optional[int] = ..., userId: _Optional[int] = ..., state: _Optional[int] = ..., index: _Optional[int] = ..., open: _Optional[bool] = ..., roomType: _Optional[int] = ..., nameKey: _Optional[str] = ..., password: _Optional[str] = ..., isInvite: _Optional[bool] = ..., capacity: _Optional[int] = ..., isGet: _Optional[bool] = ...) -> None: ...

class RoomStateRspMsg(_message.Message):
    __slots__ = ("roomState",)
    ROOMSTATE_FIELD_NUMBER: _ClassVar[int]
    roomState: int
    def __init__(self, roomState: _Optional[int] = ...) -> None: ...

class RouteMsg(_message.Message):
    __slots__ = ("x", "y", "param1")
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    PARAM1_FIELD_NUMBER: _ClassVar[int]
    x: int
    y: int
    param1: int
    def __init__(self, x: _Optional[int] = ..., y: _Optional[int] = ..., param1: _Optional[int] = ...) -> None: ...

class RouteStateMsg(_message.Message):
    __slots__ = ("userId", "userState", "path")
    USERID_FIELD_NUMBER: _ClassVar[int]
    USERSTATE_FIELD_NUMBER: _ClassVar[int]
    PATH_FIELD_NUMBER: _ClassVar[int]
    userId: int
    userState: int
    path: _containers.RepeatedCompositeFieldContainer[RouteMsg]
    def __init__(self, userId: _Optional[int] = ..., userState: _Optional[int] = ..., path: _Optional[_Iterable[_Union[RouteMsg, _Mapping]]] = ...) -> None: ...

class SNSInfoMsg(_message.Message):
    __slots__ = ("id", "userId", "nickname", "signDesc", "sex", "birthdayType", "birthYear", "birthMonth", "birthDay", "starId", "bloodType", "country", "province", "city", "headId", "job")
    ID_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    SIGNDESC_FIELD_NUMBER: _ClassVar[int]
    SEX_FIELD_NUMBER: _ClassVar[int]
    BIRTHDAYTYPE_FIELD_NUMBER: _ClassVar[int]
    BIRTHYEAR_FIELD_NUMBER: _ClassVar[int]
    BIRTHMONTH_FIELD_NUMBER: _ClassVar[int]
    BIRTHDAY_FIELD_NUMBER: _ClassVar[int]
    STARID_FIELD_NUMBER: _ClassVar[int]
    BLOODTYPE_FIELD_NUMBER: _ClassVar[int]
    COUNTRY_FIELD_NUMBER: _ClassVar[int]
    PROVINCE_FIELD_NUMBER: _ClassVar[int]
    CITY_FIELD_NUMBER: _ClassVar[int]
    HEADID_FIELD_NUMBER: _ClassVar[int]
    JOB_FIELD_NUMBER: _ClassVar[int]
    id: int
    userId: int
    nickname: str
    signDesc: str
    sex: int
    birthdayType: int
    birthYear: int
    birthMonth: int
    birthDay: int
    starId: int
    bloodType: int
    country: int
    province: int
    city: int
    headId: int
    job: int
    def __init__(self, id: _Optional[int] = ..., userId: _Optional[int] = ..., nickname: _Optional[str] = ..., signDesc: _Optional[str] = ..., sex: _Optional[int] = ..., birthdayType: _Optional[int] = ..., birthYear: _Optional[int] = ..., birthMonth: _Optional[int] = ..., birthDay: _Optional[int] = ..., starId: _Optional[int] = ..., bloodType: _Optional[int] = ..., country: _Optional[int] = ..., province: _Optional[int] = ..., city: _Optional[int] = ..., headId: _Optional[int] = ..., job: _Optional[int] = ...) -> None: ...

class SNSUpdatedMsg(_message.Message):
    __slots__ = ("snsInfo", "result")
    SNSINFO_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    snsInfo: SNSInfoMsg
    result: int
    def __init__(self, snsInfo: _Optional[_Union[SNSInfoMsg, _Mapping]] = ..., result: _Optional[int] = ...) -> None: ...

class SearchConditionMsg(_message.Message):
    __slots__ = ("pageIndex", "consortiaName", "isNewOpen")
    PAGEINDEX_FIELD_NUMBER: _ClassVar[int]
    CONSORTIANAME_FIELD_NUMBER: _ClassVar[int]
    ISNEWOPEN_FIELD_NUMBER: _ClassVar[int]
    pageIndex: int
    consortiaName: str
    isNewOpen: bool
    def __init__(self, pageIndex: _Optional[int] = ..., consortiaName: _Optional[str] = ..., isNewOpen: _Optional[bool] = ...) -> None: ...

class SearchItemReqMsg(_message.Message):
    __slots__ = ("itemName", "minLevel", "maxLevel", "quality", "job", "type", "sonType", "usable", "page", "orderBy", "orderType")
    ITEMNAME_FIELD_NUMBER: _ClassVar[int]
    MINLEVEL_FIELD_NUMBER: _ClassVar[int]
    MAXLEVEL_FIELD_NUMBER: _ClassVar[int]
    QUALITY_FIELD_NUMBER: _ClassVar[int]
    JOB_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    SONTYPE_FIELD_NUMBER: _ClassVar[int]
    USABLE_FIELD_NUMBER: _ClassVar[int]
    PAGE_FIELD_NUMBER: _ClassVar[int]
    ORDERBY_FIELD_NUMBER: _ClassVar[int]
    ORDERTYPE_FIELD_NUMBER: _ClassVar[int]
    itemName: str
    minLevel: int
    maxLevel: int
    quality: int
    job: int
    type: int
    sonType: int
    usable: bool
    page: int
    orderBy: int
    orderType: int
    def __init__(self, itemName: _Optional[str] = ..., minLevel: _Optional[int] = ..., maxLevel: _Optional[int] = ..., quality: _Optional[int] = ..., job: _Optional[int] = ..., type: _Optional[int] = ..., sonType: _Optional[int] = ..., usable: _Optional[bool] = ..., page: _Optional[int] = ..., orderBy: _Optional[int] = ..., orderType: _Optional[int] = ...) -> None: ...

class SeekNodeListMsg(_message.Message):
    __slots__ = ("seekNode",)
    SEEKNODE_FIELD_NUMBER: _ClassVar[int]
    seekNode: _containers.RepeatedCompositeFieldContainer[SeekNodeMsg]
    def __init__(self, seekNode: _Optional[_Iterable[_Union[SeekNodeMsg, _Mapping]]] = ...) -> None: ...

class SeekNodeMsg(_message.Message):
    __slots__ = ("nodeId", "nodeName", "pointX", "pointY")
    NODEID_FIELD_NUMBER: _ClassVar[int]
    NODENAME_FIELD_NUMBER: _ClassVar[int]
    POINTX_FIELD_NUMBER: _ClassVar[int]
    POINTY_FIELD_NUMBER: _ClassVar[int]
    nodeId: int
    nodeName: str
    pointX: int
    pointY: int
    def __init__(self, nodeId: _Optional[int] = ..., nodeName: _Optional[str] = ..., pointX: _Optional[int] = ..., pointY: _Optional[int] = ...) -> None: ...

class SellItemReqMsg(_message.Message):
    __slots__ = ("itemId", "itemPos", "count", "point", "fixPoint", "hour", "sellType")
    ITEMID_FIELD_NUMBER: _ClassVar[int]
    ITEMPOS_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    POINT_FIELD_NUMBER: _ClassVar[int]
    FIXPOINT_FIELD_NUMBER: _ClassVar[int]
    HOUR_FIELD_NUMBER: _ClassVar[int]
    SELLTYPE_FIELD_NUMBER: _ClassVar[int]
    itemId: int
    itemPos: int
    count: int
    point: int
    fixPoint: int
    hour: int
    sellType: int
    def __init__(self, itemId: _Optional[int] = ..., itemPos: _Optional[int] = ..., count: _Optional[int] = ..., point: _Optional[int] = ..., fixPoint: _Optional[int] = ..., hour: _Optional[int] = ..., sellType: _Optional[int] = ...) -> None: ...

class SellItemRspMsg(_message.Message):
    __slots__ = ("result", "item")
    RESULT_FIELD_NUMBER: _ClassVar[int]
    ITEM_FIELD_NUMBER: _ClassVar[int]
    result: int
    item: MallItemMsg
    def __init__(self, result: _Optional[int] = ..., item: _Optional[_Union[MallItemMsg, _Mapping]] = ...) -> None: ...

class SelledItemInfo(_message.Message):
    __slots__ = ("pos", "count", "bagType")
    POS_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    BAGTYPE_FIELD_NUMBER: _ClassVar[int]
    pos: int
    count: int
    bagType: int
    def __init__(self, pos: _Optional[int] = ..., count: _Optional[int] = ..., bagType: _Optional[int] = ...) -> None: ...

class ServenDayLeadMsg(_message.Message):
    __slots__ = ("beginTime", "statu", "singleDay")
    BEGINTIME_FIELD_NUMBER: _ClassVar[int]
    STATU_FIELD_NUMBER: _ClassVar[int]
    SINGLEDAY_FIELD_NUMBER: _ClassVar[int]
    beginTime: str
    statu: int
    singleDay: _containers.RepeatedCompositeFieldContainer[SingleDayMsg]
    def __init__(self, beginTime: _Optional[str] = ..., statu: _Optional[int] = ..., singleDay: _Optional[_Iterable[_Union[SingleDayMsg, _Mapping]]] = ...) -> None: ...

class ShopFreshReqMsg(_message.Message):
    __slots__ = ("isButton", "payType")
    ISBUTTON_FIELD_NUMBER: _ClassVar[int]
    PAYTYPE_FIELD_NUMBER: _ClassVar[int]
    isButton: bool
    payType: int
    def __init__(self, isButton: _Optional[bool] = ..., payType: _Optional[int] = ...) -> None: ...

class ShopFreshRspMsg(_message.Message):
    __slots__ = ("itemId", "freshLastdate", "isCanBuy", "buyCount", "maxBuyCount")
    ITEMID_FIELD_NUMBER: _ClassVar[int]
    FRESHLASTDATE_FIELD_NUMBER: _ClassVar[int]
    ISCANBUY_FIELD_NUMBER: _ClassVar[int]
    BUYCOUNT_FIELD_NUMBER: _ClassVar[int]
    MAXBUYCOUNT_FIELD_NUMBER: _ClassVar[int]
    itemId: _containers.RepeatedScalarFieldContainer[int]
    freshLastdate: str
    isCanBuy: _containers.RepeatedScalarFieldContainer[int]
    buyCount: int
    maxBuyCount: int
    def __init__(self, itemId: _Optional[_Iterable[int]] = ..., freshLastdate: _Optional[str] = ..., isCanBuy: _Optional[_Iterable[int]] = ..., buyCount: _Optional[int] = ..., maxBuyCount: _Optional[int] = ...) -> None: ...

class ShopItemBuyMsg(_message.Message):
    __slots__ = ("itemId", "index", "payType")
    ITEMID_FIELD_NUMBER: _ClassVar[int]
    INDEX_FIELD_NUMBER: _ClassVar[int]
    PAYTYPE_FIELD_NUMBER: _ClassVar[int]
    itemId: int
    index: int
    payType: int
    def __init__(self, itemId: _Optional[int] = ..., index: _Optional[int] = ..., payType: _Optional[int] = ...) -> None: ...

class ShopItemBuyRspMsg(_message.Message):
    __slots__ = ("result", "buyCount", "score")
    RESULT_FIELD_NUMBER: _ClassVar[int]
    BUYCOUNT_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    result: int
    buyCount: int
    score: int
    def __init__(self, result: _Optional[int] = ..., buyCount: _Optional[int] = ..., score: _Optional[int] = ...) -> None: ...

class ShopMainRspMsg(_message.Message):
    __slots__ = ("urlInfo", "goodInfo", "discountInfo")
    URLINFO_FIELD_NUMBER: _ClassVar[int]
    GOODINFO_FIELD_NUMBER: _ClassVar[int]
    DISCOUNTINFO_FIELD_NUMBER: _ClassVar[int]
    urlInfo: _containers.RepeatedCompositeFieldContainer[MainUrlInfo]
    goodInfo: _containers.RepeatedCompositeFieldContainer[MainGoodInfo]
    discountInfo: _containers.RepeatedCompositeFieldContainer[MainDiscountInfo]
    def __init__(self, urlInfo: _Optional[_Iterable[_Union[MainUrlInfo, _Mapping]]] = ..., goodInfo: _Optional[_Iterable[_Union[MainGoodInfo, _Mapping]]] = ..., discountInfo: _Optional[_Iterable[_Union[MainDiscountInfo, _Mapping]]] = ...) -> None: ...

class ShopMsg(_message.Message):
    __slots__ = ("buyInfo", "hasDataInfo", "refreshDate", "payType")
    BUYINFO_FIELD_NUMBER: _ClassVar[int]
    HASDATAINFO_FIELD_NUMBER: _ClassVar[int]
    REFRESHDATE_FIELD_NUMBER: _ClassVar[int]
    PAYTYPE_FIELD_NUMBER: _ClassVar[int]
    buyInfo: BuyInfo
    hasDataInfo: _containers.RepeatedCompositeFieldContainer[HasDataInfo]
    refreshDate: str
    payType: int
    def __init__(self, buyInfo: _Optional[_Union[BuyInfo, _Mapping]] = ..., hasDataInfo: _Optional[_Iterable[_Union[HasDataInfo, _Mapping]]] = ..., refreshDate: _Optional[str] = ..., payType: _Optional[int] = ...) -> None: ...

class SimpleArmyMsg(_message.Message):
    __slots__ = ("armyId", "playerId", "nickName", "mapId", "startPosX", "startPosY", "curPosX", "curPosY", "endPosX", "endPosY", "state", "velocity", "costTime", "departure", "destination", "command", "routeKey", "type", "armyPawn", "consortiaId", "consortiaName", "simpleHero", "tempTime", "isVip", "vipType", "storeGrade", "appellid", "fateTotalGp", "fateGrades")
    ARMYID_FIELD_NUMBER: _ClassVar[int]
    PLAYERID_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    MAPID_FIELD_NUMBER: _ClassVar[int]
    STARTPOSX_FIELD_NUMBER: _ClassVar[int]
    STARTPOSY_FIELD_NUMBER: _ClassVar[int]
    CURPOSX_FIELD_NUMBER: _ClassVar[int]
    CURPOSY_FIELD_NUMBER: _ClassVar[int]
    ENDPOSX_FIELD_NUMBER: _ClassVar[int]
    ENDPOSY_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    VELOCITY_FIELD_NUMBER: _ClassVar[int]
    COSTTIME_FIELD_NUMBER: _ClassVar[int]
    DEPARTURE_FIELD_NUMBER: _ClassVar[int]
    DESTINATION_FIELD_NUMBER: _ClassVar[int]
    COMMAND_FIELD_NUMBER: _ClassVar[int]
    ROUTEKEY_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    ARMYPAWN_FIELD_NUMBER: _ClassVar[int]
    CONSORTIAID_FIELD_NUMBER: _ClassVar[int]
    CONSORTIANAME_FIELD_NUMBER: _ClassVar[int]
    SIMPLEHERO_FIELD_NUMBER: _ClassVar[int]
    TEMPTIME_FIELD_NUMBER: _ClassVar[int]
    ISVIP_FIELD_NUMBER: _ClassVar[int]
    VIPTYPE_FIELD_NUMBER: _ClassVar[int]
    STOREGRADE_FIELD_NUMBER: _ClassVar[int]
    APPELLID_FIELD_NUMBER: _ClassVar[int]
    FATETOTALGP_FIELD_NUMBER: _ClassVar[int]
    FATEGRADES_FIELD_NUMBER: _ClassVar[int]
    armyId: int
    playerId: int
    nickName: str
    mapId: int
    startPosX: int
    startPosY: int
    curPosX: int
    curPosY: int
    endPosX: int
    endPosY: int
    state: int
    velocity: int
    costTime: int
    departure: str
    destination: str
    command: int
    routeKey: _containers.RepeatedScalarFieldContainer[str]
    type: int
    armyPawn: _containers.RepeatedCompositeFieldContainer[SimpleArmyPawnMsg]
    consortiaId: int
    consortiaName: str
    simpleHero: SimpleHeroMsg
    tempTime: int
    isVip: bool
    vipType: int
    storeGrade: int
    appellid: int
    fateTotalGp: int
    fateGrades: str
    def __init__(self, armyId: _Optional[int] = ..., playerId: _Optional[int] = ..., nickName: _Optional[str] = ..., mapId: _Optional[int] = ..., startPosX: _Optional[int] = ..., startPosY: _Optional[int] = ..., curPosX: _Optional[int] = ..., curPosY: _Optional[int] = ..., endPosX: _Optional[int] = ..., endPosY: _Optional[int] = ..., state: _Optional[int] = ..., velocity: _Optional[int] = ..., costTime: _Optional[int] = ..., departure: _Optional[str] = ..., destination: _Optional[str] = ..., command: _Optional[int] = ..., routeKey: _Optional[_Iterable[str]] = ..., type: _Optional[int] = ..., armyPawn: _Optional[_Iterable[_Union[SimpleArmyPawnMsg, _Mapping]]] = ..., consortiaId: _Optional[int] = ..., consortiaName: _Optional[str] = ..., simpleHero: _Optional[_Union[SimpleHeroMsg, _Mapping]] = ..., tempTime: _Optional[int] = ..., isVip: _Optional[bool] = ..., vipType: _Optional[int] = ..., storeGrade: _Optional[int] = ..., appellid: _Optional[int] = ..., fateTotalGp: _Optional[int] = ..., fateGrades: _Optional[str] = ...) -> None: ...

class SimpleArmyPawnMsg(_message.Message):
    __slots__ = ("id", "armyId", "sites", "sonType", "tempateId", "ownPawns", "live", "attack", "defence", "magicAttack", "magicDefence", "skill", "forceHit", "parry")
    ID_FIELD_NUMBER: _ClassVar[int]
    ARMYID_FIELD_NUMBER: _ClassVar[int]
    SITES_FIELD_NUMBER: _ClassVar[int]
    SONTYPE_FIELD_NUMBER: _ClassVar[int]
    TEMPATEID_FIELD_NUMBER: _ClassVar[int]
    OWNPAWNS_FIELD_NUMBER: _ClassVar[int]
    LIVE_FIELD_NUMBER: _ClassVar[int]
    ATTACK_FIELD_NUMBER: _ClassVar[int]
    DEFENCE_FIELD_NUMBER: _ClassVar[int]
    MAGICATTACK_FIELD_NUMBER: _ClassVar[int]
    MAGICDEFENCE_FIELD_NUMBER: _ClassVar[int]
    SKILL_FIELD_NUMBER: _ClassVar[int]
    FORCEHIT_FIELD_NUMBER: _ClassVar[int]
    PARRY_FIELD_NUMBER: _ClassVar[int]
    id: int
    armyId: int
    sites: int
    sonType: int
    tempateId: int
    ownPawns: int
    live: int
    attack: int
    defence: int
    magicAttack: int
    magicDefence: int
    skill: int
    forceHit: int
    parry: int
    def __init__(self, id: _Optional[int] = ..., armyId: _Optional[int] = ..., sites: _Optional[int] = ..., sonType: _Optional[int] = ..., tempateId: _Optional[int] = ..., ownPawns: _Optional[int] = ..., live: _Optional[int] = ..., attack: _Optional[int] = ..., defence: _Optional[int] = ..., magicAttack: _Optional[int] = ..., magicDefence: _Optional[int] = ..., skill: _Optional[int] = ..., forceHit: _Optional[int] = ..., parry: _Optional[int] = ...) -> None: ...

class SimpleHeroInfoMsg(_message.Message):
    __slots__ = ("heroId", "nickName", "tempateId", "playerId", "remainPoint", "skillPoint", "skillScript", "fastKey", "hp", "blood", "bloodId", "totalPower", "totalAgility", "totalIntellect", "totalCaptain", "totalPhysique", "totalPhyAttack", "totalPhyDefence", "totalMagicAttack", "totalMagicDefence", "totalForceHit", "totalParry", "totalConatArmy", "totalLive", "basePower", "baseAgility", "baseIntellect", "baseCaptain", "basePhysique", "basePhyAttack", "basePhyDefence", "baseMagicAttack", "baseMagicDefence", "baseForceHit", "baseParry", "baseConatArmy", "baseLive", "powerPoint", "agilityPoint", "intellectPoint", "captainPoint", "physiquePoint", "fightPos", "skillIndex", "isActiveSecond", "headId", "talentPoint", "talentGrade", "talentSkill", "grade", "arm", "cloth", "wing", "fightingCapacity", "serverName", "hat", "fashionArm", "fashionCloth", "hide", "rune", "fireResi", "waterResi", "electResi", "windResi", "darkResi", "lightResi", "reduceResi", "totalStrength", "baseStrength", "totalTenacity", "baseTenacity")
    HEROID_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    TEMPATEID_FIELD_NUMBER: _ClassVar[int]
    PLAYERID_FIELD_NUMBER: _ClassVar[int]
    REMAINPOINT_FIELD_NUMBER: _ClassVar[int]
    SKILLPOINT_FIELD_NUMBER: _ClassVar[int]
    SKILLSCRIPT_FIELD_NUMBER: _ClassVar[int]
    FASTKEY_FIELD_NUMBER: _ClassVar[int]
    HP_FIELD_NUMBER: _ClassVar[int]
    BLOOD_FIELD_NUMBER: _ClassVar[int]
    BLOODID_FIELD_NUMBER: _ClassVar[int]
    TOTALPOWER_FIELD_NUMBER: _ClassVar[int]
    TOTALAGILITY_FIELD_NUMBER: _ClassVar[int]
    TOTALINTELLECT_FIELD_NUMBER: _ClassVar[int]
    TOTALCAPTAIN_FIELD_NUMBER: _ClassVar[int]
    TOTALPHYSIQUE_FIELD_NUMBER: _ClassVar[int]
    TOTALPHYATTACK_FIELD_NUMBER: _ClassVar[int]
    TOTALPHYDEFENCE_FIELD_NUMBER: _ClassVar[int]
    TOTALMAGICATTACK_FIELD_NUMBER: _ClassVar[int]
    TOTALMAGICDEFENCE_FIELD_NUMBER: _ClassVar[int]
    TOTALFORCEHIT_FIELD_NUMBER: _ClassVar[int]
    TOTALPARRY_FIELD_NUMBER: _ClassVar[int]
    TOTALCONATARMY_FIELD_NUMBER: _ClassVar[int]
    TOTALLIVE_FIELD_NUMBER: _ClassVar[int]
    BASEPOWER_FIELD_NUMBER: _ClassVar[int]
    BASEAGILITY_FIELD_NUMBER: _ClassVar[int]
    BASEINTELLECT_FIELD_NUMBER: _ClassVar[int]
    BASECAPTAIN_FIELD_NUMBER: _ClassVar[int]
    BASEPHYSIQUE_FIELD_NUMBER: _ClassVar[int]
    BASEPHYATTACK_FIELD_NUMBER: _ClassVar[int]
    BASEPHYDEFENCE_FIELD_NUMBER: _ClassVar[int]
    BASEMAGICATTACK_FIELD_NUMBER: _ClassVar[int]
    BASEMAGICDEFENCE_FIELD_NUMBER: _ClassVar[int]
    BASEFORCEHIT_FIELD_NUMBER: _ClassVar[int]
    BASEPARRY_FIELD_NUMBER: _ClassVar[int]
    BASECONATARMY_FIELD_NUMBER: _ClassVar[int]
    BASELIVE_FIELD_NUMBER: _ClassVar[int]
    POWERPOINT_FIELD_NUMBER: _ClassVar[int]
    AGILITYPOINT_FIELD_NUMBER: _ClassVar[int]
    INTELLECTPOINT_FIELD_NUMBER: _ClassVar[int]
    CAPTAINPOINT_FIELD_NUMBER: _ClassVar[int]
    PHYSIQUEPOINT_FIELD_NUMBER: _ClassVar[int]
    FIGHTPOS_FIELD_NUMBER: _ClassVar[int]
    SKILLINDEX_FIELD_NUMBER: _ClassVar[int]
    ISACTIVESECOND_FIELD_NUMBER: _ClassVar[int]
    HEADID_FIELD_NUMBER: _ClassVar[int]
    TALENTPOINT_FIELD_NUMBER: _ClassVar[int]
    TALENTGRADE_FIELD_NUMBER: _ClassVar[int]
    TALENTSKILL_FIELD_NUMBER: _ClassVar[int]
    GRADE_FIELD_NUMBER: _ClassVar[int]
    ARM_FIELD_NUMBER: _ClassVar[int]
    CLOTH_FIELD_NUMBER: _ClassVar[int]
    WING_FIELD_NUMBER: _ClassVar[int]
    FIGHTINGCAPACITY_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    HAT_FIELD_NUMBER: _ClassVar[int]
    FASHIONARM_FIELD_NUMBER: _ClassVar[int]
    FASHIONCLOTH_FIELD_NUMBER: _ClassVar[int]
    HIDE_FIELD_NUMBER: _ClassVar[int]
    RUNE_FIELD_NUMBER: _ClassVar[int]
    FIRERESI_FIELD_NUMBER: _ClassVar[int]
    WATERRESI_FIELD_NUMBER: _ClassVar[int]
    ELECTRESI_FIELD_NUMBER: _ClassVar[int]
    WINDRESI_FIELD_NUMBER: _ClassVar[int]
    DARKRESI_FIELD_NUMBER: _ClassVar[int]
    LIGHTRESI_FIELD_NUMBER: _ClassVar[int]
    REDUCERESI_FIELD_NUMBER: _ClassVar[int]
    TOTALSTRENGTH_FIELD_NUMBER: _ClassVar[int]
    BASESTRENGTH_FIELD_NUMBER: _ClassVar[int]
    TOTALTENACITY_FIELD_NUMBER: _ClassVar[int]
    BASETENACITY_FIELD_NUMBER: _ClassVar[int]
    heroId: int
    nickName: str
    tempateId: int
    playerId: int
    remainPoint: int
    skillPoint: int
    skillScript: str
    fastKey: str
    hp: int
    blood: int
    bloodId: int
    totalPower: int
    totalAgility: int
    totalIntellect: int
    totalCaptain: int
    totalPhysique: int
    totalPhyAttack: int
    totalPhyDefence: int
    totalMagicAttack: int
    totalMagicDefence: int
    totalForceHit: int
    totalParry: int
    totalConatArmy: int
    totalLive: int
    basePower: int
    baseAgility: int
    baseIntellect: int
    baseCaptain: int
    basePhysique: int
    basePhyAttack: int
    basePhyDefence: int
    baseMagicAttack: int
    baseMagicDefence: int
    baseForceHit: int
    baseParry: int
    baseConatArmy: int
    baseLive: int
    powerPoint: int
    agilityPoint: int
    intellectPoint: int
    captainPoint: int
    physiquePoint: int
    fightPos: int
    skillIndex: int
    isActiveSecond: bool
    headId: int
    talentPoint: int
    talentGrade: int
    talentSkill: str
    grade: int
    arm: str
    cloth: str
    wing: str
    fightingCapacity: int
    serverName: str
    hat: str
    fashionArm: str
    fashionCloth: str
    hide: bool
    rune: HeroRuneMsg
    fireResi: int
    waterResi: int
    electResi: int
    windResi: int
    darkResi: int
    lightResi: int
    reduceResi: int
    totalStrength: int
    baseStrength: int
    totalTenacity: int
    baseTenacity: int
    def __init__(self, heroId: _Optional[int] = ..., nickName: _Optional[str] = ..., tempateId: _Optional[int] = ..., playerId: _Optional[int] = ..., remainPoint: _Optional[int] = ..., skillPoint: _Optional[int] = ..., skillScript: _Optional[str] = ..., fastKey: _Optional[str] = ..., hp: _Optional[int] = ..., blood: _Optional[int] = ..., bloodId: _Optional[int] = ..., totalPower: _Optional[int] = ..., totalAgility: _Optional[int] = ..., totalIntellect: _Optional[int] = ..., totalCaptain: _Optional[int] = ..., totalPhysique: _Optional[int] = ..., totalPhyAttack: _Optional[int] = ..., totalPhyDefence: _Optional[int] = ..., totalMagicAttack: _Optional[int] = ..., totalMagicDefence: _Optional[int] = ..., totalForceHit: _Optional[int] = ..., totalParry: _Optional[int] = ..., totalConatArmy: _Optional[int] = ..., totalLive: _Optional[int] = ..., basePower: _Optional[int] = ..., baseAgility: _Optional[int] = ..., baseIntellect: _Optional[int] = ..., baseCaptain: _Optional[int] = ..., basePhysique: _Optional[int] = ..., basePhyAttack: _Optional[int] = ..., basePhyDefence: _Optional[int] = ..., baseMagicAttack: _Optional[int] = ..., baseMagicDefence: _Optional[int] = ..., baseForceHit: _Optional[int] = ..., baseParry: _Optional[int] = ..., baseConatArmy: _Optional[int] = ..., baseLive: _Optional[int] = ..., powerPoint: _Optional[int] = ..., agilityPoint: _Optional[int] = ..., intellectPoint: _Optional[int] = ..., captainPoint: _Optional[int] = ..., physiquePoint: _Optional[int] = ..., fightPos: _Optional[int] = ..., skillIndex: _Optional[int] = ..., isActiveSecond: _Optional[bool] = ..., headId: _Optional[int] = ..., talentPoint: _Optional[int] = ..., talentGrade: _Optional[int] = ..., talentSkill: _Optional[str] = ..., grade: _Optional[int] = ..., arm: _Optional[str] = ..., cloth: _Optional[str] = ..., wing: _Optional[str] = ..., fightingCapacity: _Optional[int] = ..., serverName: _Optional[str] = ..., hat: _Optional[str] = ..., fashionArm: _Optional[str] = ..., fashionCloth: _Optional[str] = ..., hide: _Optional[bool] = ..., rune: _Optional[_Union[HeroRuneMsg, _Mapping]] = ..., fireResi: _Optional[int] = ..., waterResi: _Optional[int] = ..., electResi: _Optional[int] = ..., windResi: _Optional[int] = ..., darkResi: _Optional[int] = ..., lightResi: _Optional[int] = ..., reduceResi: _Optional[int] = ..., totalStrength: _Optional[int] = ..., baseStrength: _Optional[int] = ..., totalTenacity: _Optional[int] = ..., baseTenacity: _Optional[int] = ...) -> None: ...

class SimpleHeroMsg(_message.Message):
    __slots__ = ("heroId", "nickName", "tempateId", "playerId", "totalPower", "totalAgility", "totalIntellect", "totalCaptain", "totalPhysique", "totalPhyAttack", "totalPhyDefence", "totalMagicAttack", "totalMagicDefence", "totalForceHit", "totalParry", "totalConatArmy", "totalLive", "remainPoint", "skillPoint", "skillScript", "bagJoin", "consortiaJoin", "fastKey", "hp", "blood", "bloodId", "basePower", "baseAgility", "baseIntellect", "baseCaptain", "basePhysique", "basePhyAttack", "basePhyDefence", "baseMagicAttack", "baseMagicDefence", "baseForceHit", "baseParry", "baseConatArmy", "baseLive", "powerPoint", "agilityPoint", "intellectPoint", "captainPoint", "physiquePoint", "skillIndex", "isActiveSecond", "headId", "totalGeste", "totalCharm", "fireResi", "waterResi", "electResi", "windResi", "darkResi", "lightResi", "reduceResi", "totalStrength", "baseStrength", "totalTenacity", "baseTenacity", "fashionAddPower", "fashionAddArmor", "fashionAddIntellect", "fashionAddLife", "ringGrade", "nickNameB")
    HEROID_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    TEMPATEID_FIELD_NUMBER: _ClassVar[int]
    PLAYERID_FIELD_NUMBER: _ClassVar[int]
    TOTALPOWER_FIELD_NUMBER: _ClassVar[int]
    TOTALAGILITY_FIELD_NUMBER: _ClassVar[int]
    TOTALINTELLECT_FIELD_NUMBER: _ClassVar[int]
    TOTALCAPTAIN_FIELD_NUMBER: _ClassVar[int]
    TOTALPHYSIQUE_FIELD_NUMBER: _ClassVar[int]
    TOTALPHYATTACK_FIELD_NUMBER: _ClassVar[int]
    TOTALPHYDEFENCE_FIELD_NUMBER: _ClassVar[int]
    TOTALMAGICATTACK_FIELD_NUMBER: _ClassVar[int]
    TOTALMAGICDEFENCE_FIELD_NUMBER: _ClassVar[int]
    TOTALFORCEHIT_FIELD_NUMBER: _ClassVar[int]
    TOTALPARRY_FIELD_NUMBER: _ClassVar[int]
    TOTALCONATARMY_FIELD_NUMBER: _ClassVar[int]
    TOTALLIVE_FIELD_NUMBER: _ClassVar[int]
    REMAINPOINT_FIELD_NUMBER: _ClassVar[int]
    SKILLPOINT_FIELD_NUMBER: _ClassVar[int]
    SKILLSCRIPT_FIELD_NUMBER: _ClassVar[int]
    BAGJOIN_FIELD_NUMBER: _ClassVar[int]
    CONSORTIAJOIN_FIELD_NUMBER: _ClassVar[int]
    FASTKEY_FIELD_NUMBER: _ClassVar[int]
    HP_FIELD_NUMBER: _ClassVar[int]
    BLOOD_FIELD_NUMBER: _ClassVar[int]
    BLOODID_FIELD_NUMBER: _ClassVar[int]
    BASEPOWER_FIELD_NUMBER: _ClassVar[int]
    BASEAGILITY_FIELD_NUMBER: _ClassVar[int]
    BASEINTELLECT_FIELD_NUMBER: _ClassVar[int]
    BASECAPTAIN_FIELD_NUMBER: _ClassVar[int]
    BASEPHYSIQUE_FIELD_NUMBER: _ClassVar[int]
    BASEPHYATTACK_FIELD_NUMBER: _ClassVar[int]
    BASEPHYDEFENCE_FIELD_NUMBER: _ClassVar[int]
    BASEMAGICATTACK_FIELD_NUMBER: _ClassVar[int]
    BASEMAGICDEFENCE_FIELD_NUMBER: _ClassVar[int]
    BASEFORCEHIT_FIELD_NUMBER: _ClassVar[int]
    BASEPARRY_FIELD_NUMBER: _ClassVar[int]
    BASECONATARMY_FIELD_NUMBER: _ClassVar[int]
    BASELIVE_FIELD_NUMBER: _ClassVar[int]
    POWERPOINT_FIELD_NUMBER: _ClassVar[int]
    AGILITYPOINT_FIELD_NUMBER: _ClassVar[int]
    INTELLECTPOINT_FIELD_NUMBER: _ClassVar[int]
    CAPTAINPOINT_FIELD_NUMBER: _ClassVar[int]
    PHYSIQUEPOINT_FIELD_NUMBER: _ClassVar[int]
    SKILLINDEX_FIELD_NUMBER: _ClassVar[int]
    ISACTIVESECOND_FIELD_NUMBER: _ClassVar[int]
    HEADID_FIELD_NUMBER: _ClassVar[int]
    TOTALGESTE_FIELD_NUMBER: _ClassVar[int]
    TOTALCHARM_FIELD_NUMBER: _ClassVar[int]
    FIRERESI_FIELD_NUMBER: _ClassVar[int]
    WATERRESI_FIELD_NUMBER: _ClassVar[int]
    ELECTRESI_FIELD_NUMBER: _ClassVar[int]
    WINDRESI_FIELD_NUMBER: _ClassVar[int]
    DARKRESI_FIELD_NUMBER: _ClassVar[int]
    LIGHTRESI_FIELD_NUMBER: _ClassVar[int]
    REDUCERESI_FIELD_NUMBER: _ClassVar[int]
    TOTALSTRENGTH_FIELD_NUMBER: _ClassVar[int]
    BASESTRENGTH_FIELD_NUMBER: _ClassVar[int]
    TOTALTENACITY_FIELD_NUMBER: _ClassVar[int]
    BASETENACITY_FIELD_NUMBER: _ClassVar[int]
    FASHIONADDPOWER_FIELD_NUMBER: _ClassVar[int]
    FASHIONADDARMOR_FIELD_NUMBER: _ClassVar[int]
    FASHIONADDINTELLECT_FIELD_NUMBER: _ClassVar[int]
    FASHIONADDLIFE_FIELD_NUMBER: _ClassVar[int]
    RINGGRADE_FIELD_NUMBER: _ClassVar[int]
    NICKNAMEB_FIELD_NUMBER: _ClassVar[int]
    heroId: int
    nickName: str
    tempateId: int
    playerId: int
    totalPower: int
    totalAgility: int
    totalIntellect: int
    totalCaptain: int
    totalPhysique: int
    totalPhyAttack: int
    totalPhyDefence: int
    totalMagicAttack: int
    totalMagicDefence: int
    totalForceHit: int
    totalParry: int
    totalConatArmy: int
    totalLive: int
    remainPoint: int
    skillPoint: int
    skillScript: str
    bagJoin: str
    consortiaJoin: str
    fastKey: str
    hp: int
    blood: int
    bloodId: int
    basePower: int
    baseAgility: int
    baseIntellect: int
    baseCaptain: int
    basePhysique: int
    basePhyAttack: int
    basePhyDefence: int
    baseMagicAttack: int
    baseMagicDefence: int
    baseForceHit: int
    baseParry: int
    baseConatArmy: int
    baseLive: int
    powerPoint: int
    agilityPoint: int
    intellectPoint: int
    captainPoint: int
    physiquePoint: int
    skillIndex: int
    isActiveSecond: bool
    headId: int
    totalGeste: int
    totalCharm: int
    fireResi: int
    waterResi: int
    electResi: int
    windResi: int
    darkResi: int
    lightResi: int
    reduceResi: int
    totalStrength: int
    baseStrength: int
    totalTenacity: int
    baseTenacity: int
    fashionAddPower: int
    fashionAddArmor: int
    fashionAddIntellect: int
    fashionAddLife: int
    ringGrade: int
    nickNameB: str
    def __init__(self, heroId: _Optional[int] = ..., nickName: _Optional[str] = ..., tempateId: _Optional[int] = ..., playerId: _Optional[int] = ..., totalPower: _Optional[int] = ..., totalAgility: _Optional[int] = ..., totalIntellect: _Optional[int] = ..., totalCaptain: _Optional[int] = ..., totalPhysique: _Optional[int] = ..., totalPhyAttack: _Optional[int] = ..., totalPhyDefence: _Optional[int] = ..., totalMagicAttack: _Optional[int] = ..., totalMagicDefence: _Optional[int] = ..., totalForceHit: _Optional[int] = ..., totalParry: _Optional[int] = ..., totalConatArmy: _Optional[int] = ..., totalLive: _Optional[int] = ..., remainPoint: _Optional[int] = ..., skillPoint: _Optional[int] = ..., skillScript: _Optional[str] = ..., bagJoin: _Optional[str] = ..., consortiaJoin: _Optional[str] = ..., fastKey: _Optional[str] = ..., hp: _Optional[int] = ..., blood: _Optional[int] = ..., bloodId: _Optional[int] = ..., basePower: _Optional[int] = ..., baseAgility: _Optional[int] = ..., baseIntellect: _Optional[int] = ..., baseCaptain: _Optional[int] = ..., basePhysique: _Optional[int] = ..., basePhyAttack: _Optional[int] = ..., basePhyDefence: _Optional[int] = ..., baseMagicAttack: _Optional[int] = ..., baseMagicDefence: _Optional[int] = ..., baseForceHit: _Optional[int] = ..., baseParry: _Optional[int] = ..., baseConatArmy: _Optional[int] = ..., baseLive: _Optional[int] = ..., powerPoint: _Optional[int] = ..., agilityPoint: _Optional[int] = ..., intellectPoint: _Optional[int] = ..., captainPoint: _Optional[int] = ..., physiquePoint: _Optional[int] = ..., skillIndex: _Optional[int] = ..., isActiveSecond: _Optional[bool] = ..., headId: _Optional[int] = ..., totalGeste: _Optional[int] = ..., totalCharm: _Optional[int] = ..., fireResi: _Optional[int] = ..., waterResi: _Optional[int] = ..., electResi: _Optional[int] = ..., windResi: _Optional[int] = ..., darkResi: _Optional[int] = ..., lightResi: _Optional[int] = ..., reduceResi: _Optional[int] = ..., totalStrength: _Optional[int] = ..., baseStrength: _Optional[int] = ..., totalTenacity: _Optional[int] = ..., baseTenacity: _Optional[int] = ..., fashionAddPower: _Optional[int] = ..., fashionAddArmor: _Optional[int] = ..., fashionAddIntellect: _Optional[int] = ..., fashionAddLife: _Optional[int] = ..., ringGrade: _Optional[int] = ..., nickNameB: _Optional[str] = ...) -> None: ...

class SimpleItemInfoMsg(_message.Message):
    __slots__ = ("id", "templateId", "pos", "exist", "objectId", "bagType", "bind", "used", "validDate", "beginDate", "count", "attack", "defence", "agility", "ability", "captain", "strengthenGrade", "join_1", "join_2", "join_3", "join_4", "randomSkill_1", "randomSkill_2", "randomSkill_3", "randomSkill_4", "randomSkill_5", "isNew", "userId", "isShow", "isNewItems", "property1", "strength", "tenacity", "mouldGrade", "appraisalSkill", "isLocked", "descTemplateId", "lifeSkill")
    ID_FIELD_NUMBER: _ClassVar[int]
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    POS_FIELD_NUMBER: _ClassVar[int]
    EXIST_FIELD_NUMBER: _ClassVar[int]
    OBJECTID_FIELD_NUMBER: _ClassVar[int]
    BAGTYPE_FIELD_NUMBER: _ClassVar[int]
    BIND_FIELD_NUMBER: _ClassVar[int]
    USED_FIELD_NUMBER: _ClassVar[int]
    VALIDDATE_FIELD_NUMBER: _ClassVar[int]
    BEGINDATE_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    ATTACK_FIELD_NUMBER: _ClassVar[int]
    DEFENCE_FIELD_NUMBER: _ClassVar[int]
    AGILITY_FIELD_NUMBER: _ClassVar[int]
    ABILITY_FIELD_NUMBER: _ClassVar[int]
    CAPTAIN_FIELD_NUMBER: _ClassVar[int]
    STRENGTHENGRADE_FIELD_NUMBER: _ClassVar[int]
    JOIN_1_FIELD_NUMBER: _ClassVar[int]
    JOIN_2_FIELD_NUMBER: _ClassVar[int]
    JOIN_3_FIELD_NUMBER: _ClassVar[int]
    JOIN_4_FIELD_NUMBER: _ClassVar[int]
    RANDOMSKILL_1_FIELD_NUMBER: _ClassVar[int]
    RANDOMSKILL_2_FIELD_NUMBER: _ClassVar[int]
    RANDOMSKILL_3_FIELD_NUMBER: _ClassVar[int]
    RANDOMSKILL_4_FIELD_NUMBER: _ClassVar[int]
    RANDOMSKILL_5_FIELD_NUMBER: _ClassVar[int]
    ISNEW_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    ISSHOW_FIELD_NUMBER: _ClassVar[int]
    ISNEWITEMS_FIELD_NUMBER: _ClassVar[int]
    PROPERTY1_FIELD_NUMBER: _ClassVar[int]
    STRENGTH_FIELD_NUMBER: _ClassVar[int]
    TENACITY_FIELD_NUMBER: _ClassVar[int]
    MOULDGRADE_FIELD_NUMBER: _ClassVar[int]
    APPRAISALSKILL_FIELD_NUMBER: _ClassVar[int]
    ISLOCKED_FIELD_NUMBER: _ClassVar[int]
    DESCTEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    LIFESKILL_FIELD_NUMBER: _ClassVar[int]
    id: int
    templateId: int
    pos: int
    exist: bool
    objectId: int
    bagType: int
    bind: bool
    used: bool
    validDate: int
    beginDate: str
    count: int
    attack: int
    defence: int
    agility: int
    ability: int
    captain: int
    strengthenGrade: int
    join_1: int
    join_2: int
    join_3: int
    join_4: int
    randomSkill_1: int
    randomSkill_2: int
    randomSkill_3: int
    randomSkill_4: int
    randomSkill_5: int
    isNew: bool
    userId: int
    isShow: bool
    isNewItems: bool
    property1: str
    strength: int
    tenacity: int
    mouldGrade: int
    appraisalSkill: int
    isLocked: bool
    descTemplateId: int
    lifeSkill: int
    def __init__(self, id: _Optional[int] = ..., templateId: _Optional[int] = ..., pos: _Optional[int] = ..., exist: _Optional[bool] = ..., objectId: _Optional[int] = ..., bagType: _Optional[int] = ..., bind: _Optional[bool] = ..., used: _Optional[bool] = ..., validDate: _Optional[int] = ..., beginDate: _Optional[str] = ..., count: _Optional[int] = ..., attack: _Optional[int] = ..., defence: _Optional[int] = ..., agility: _Optional[int] = ..., ability: _Optional[int] = ..., captain: _Optional[int] = ..., strengthenGrade: _Optional[int] = ..., join_1: _Optional[int] = ..., join_2: _Optional[int] = ..., join_3: _Optional[int] = ..., join_4: _Optional[int] = ..., randomSkill_1: _Optional[int] = ..., randomSkill_2: _Optional[int] = ..., randomSkill_3: _Optional[int] = ..., randomSkill_4: _Optional[int] = ..., randomSkill_5: _Optional[int] = ..., isNew: _Optional[bool] = ..., userId: _Optional[int] = ..., isShow: _Optional[bool] = ..., isNewItems: _Optional[bool] = ..., property1: _Optional[str] = ..., strength: _Optional[int] = ..., tenacity: _Optional[int] = ..., mouldGrade: _Optional[int] = ..., appraisalSkill: _Optional[int] = ..., isLocked: _Optional[bool] = ..., descTemplateId: _Optional[int] = ..., lifeSkill: _Optional[int] = ...) -> None: ...

class SimplePlayerInfoMsg(_message.Message):
    __slots__ = ("userId", "nickName", "isExist", "sexs", "pics", "camp", "state", "consortiaID", "strategy", "consortiaName", "consortiaOffer", "claimId", "claimName", "grades", "gp", "repute", "logOutTime", "dutyId", "parameter1", "gpOrder", "fightingCapacity", "matchWin", "matchFailed", "right", "challengeRank", "job", "consortiaTotalOffer", "storeGrade", "storeGp", "isTeamPlayer", "role", "isVip", "vipType", "isInwar", "headId", "crossGuildTeamId")
    USERID_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    ISEXIST_FIELD_NUMBER: _ClassVar[int]
    SEXS_FIELD_NUMBER: _ClassVar[int]
    PICS_FIELD_NUMBER: _ClassVar[int]
    CAMP_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    CONSORTIAID_FIELD_NUMBER: _ClassVar[int]
    STRATEGY_FIELD_NUMBER: _ClassVar[int]
    CONSORTIANAME_FIELD_NUMBER: _ClassVar[int]
    CONSORTIAOFFER_FIELD_NUMBER: _ClassVar[int]
    CLAIMID_FIELD_NUMBER: _ClassVar[int]
    CLAIMNAME_FIELD_NUMBER: _ClassVar[int]
    GRADES_FIELD_NUMBER: _ClassVar[int]
    GP_FIELD_NUMBER: _ClassVar[int]
    REPUTE_FIELD_NUMBER: _ClassVar[int]
    LOGOUTTIME_FIELD_NUMBER: _ClassVar[int]
    DUTYID_FIELD_NUMBER: _ClassVar[int]
    PARAMETER1_FIELD_NUMBER: _ClassVar[int]
    GPORDER_FIELD_NUMBER: _ClassVar[int]
    FIGHTINGCAPACITY_FIELD_NUMBER: _ClassVar[int]
    MATCHWIN_FIELD_NUMBER: _ClassVar[int]
    MATCHFAILED_FIELD_NUMBER: _ClassVar[int]
    RIGHT_FIELD_NUMBER: _ClassVar[int]
    CHALLENGERANK_FIELD_NUMBER: _ClassVar[int]
    JOB_FIELD_NUMBER: _ClassVar[int]
    CONSORTIATOTALOFFER_FIELD_NUMBER: _ClassVar[int]
    STOREGRADE_FIELD_NUMBER: _ClassVar[int]
    STOREGP_FIELD_NUMBER: _ClassVar[int]
    ISTEAMPLAYER_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    ISVIP_FIELD_NUMBER: _ClassVar[int]
    VIPTYPE_FIELD_NUMBER: _ClassVar[int]
    ISINWAR_FIELD_NUMBER: _ClassVar[int]
    HEADID_FIELD_NUMBER: _ClassVar[int]
    CROSSGUILDTEAMID_FIELD_NUMBER: _ClassVar[int]
    userId: int
    nickName: str
    isExist: int
    sexs: int
    pics: int
    camp: int
    state: int
    consortiaID: int
    strategy: int
    consortiaName: str
    consortiaOffer: int
    claimId: int
    claimName: str
    grades: int
    gp: int
    repute: int
    logOutTime: str
    dutyId: int
    parameter1: int
    gpOrder: int
    fightingCapacity: int
    matchWin: int
    matchFailed: int
    right: int
    challengeRank: int
    job: int
    consortiaTotalOffer: int
    storeGrade: int
    storeGp: int
    isTeamPlayer: bool
    role: int
    isVip: bool
    vipType: int
    isInwar: int
    headId: int
    crossGuildTeamId: int
    def __init__(self, userId: _Optional[int] = ..., nickName: _Optional[str] = ..., isExist: _Optional[int] = ..., sexs: _Optional[int] = ..., pics: _Optional[int] = ..., camp: _Optional[int] = ..., state: _Optional[int] = ..., consortiaID: _Optional[int] = ..., strategy: _Optional[int] = ..., consortiaName: _Optional[str] = ..., consortiaOffer: _Optional[int] = ..., claimId: _Optional[int] = ..., claimName: _Optional[str] = ..., grades: _Optional[int] = ..., gp: _Optional[int] = ..., repute: _Optional[int] = ..., logOutTime: _Optional[str] = ..., dutyId: _Optional[int] = ..., parameter1: _Optional[int] = ..., gpOrder: _Optional[int] = ..., fightingCapacity: _Optional[int] = ..., matchWin: _Optional[int] = ..., matchFailed: _Optional[int] = ..., right: _Optional[int] = ..., challengeRank: _Optional[int] = ..., job: _Optional[int] = ..., consortiaTotalOffer: _Optional[int] = ..., storeGrade: _Optional[int] = ..., storeGp: _Optional[int] = ..., isTeamPlayer: _Optional[bool] = ..., role: _Optional[int] = ..., isVip: _Optional[bool] = ..., vipType: _Optional[int] = ..., isInwar: _Optional[int] = ..., headId: _Optional[int] = ..., crossGuildTeamId: _Optional[int] = ...) -> None: ...

class SimplePlayerListRspMsg(_message.Message):
    __slots__ = ("totalRows", "playerInfo", "uuid")
    TOTALROWS_FIELD_NUMBER: _ClassVar[int]
    PLAYERINFO_FIELD_NUMBER: _ClassVar[int]
    UUID_FIELD_NUMBER: _ClassVar[int]
    totalRows: int
    playerInfo: _containers.RepeatedCompositeFieldContainer[SimplePlayerInfoMsg]
    uuid: str
    def __init__(self, totalRows: _Optional[int] = ..., playerInfo: _Optional[_Iterable[_Union[SimplePlayerInfoMsg, _Mapping]]] = ..., uuid: _Optional[str] = ...) -> None: ...

class SimplePlayerSearchReqMsg(_message.Message):
    __slots__ = ("otherNickname",)
    OTHERNICKNAME_FIELD_NUMBER: _ClassVar[int]
    otherNickname: str
    def __init__(self, otherNickname: _Optional[str] = ...) -> None: ...

class SimplePlayerSearchRspMsg(_message.Message):
    __slots__ = ("info",)
    INFO_FIELD_NUMBER: _ClassVar[int]
    info: SimplePlayerInfoMsg
    def __init__(self, info: _Optional[_Union[SimplePlayerInfoMsg, _Mapping]] = ...) -> None: ...

class SimplePowCardFightInfoMsg(_message.Message):
    __slots__ = ("op", "userid", "campType", "add")
    OP_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    CAMPTYPE_FIELD_NUMBER: _ClassVar[int]
    ADD_FIELD_NUMBER: _ClassVar[int]
    op: int
    userid: int
    campType: int
    add: int
    def __init__(self, op: _Optional[int] = ..., userid: _Optional[int] = ..., campType: _Optional[int] = ..., add: _Optional[int] = ...) -> None: ...

class SimplePropertyListMsg(_message.Message):
    __slots__ = ("param1", "param2", "param3", "property")
    PARAM1_FIELD_NUMBER: _ClassVar[int]
    PARAM2_FIELD_NUMBER: _ClassVar[int]
    PARAM3_FIELD_NUMBER: _ClassVar[int]
    PROPERTY_FIELD_NUMBER: _ClassVar[int]
    param1: int
    param2: int
    param3: str
    property: _containers.RepeatedCompositeFieldContainer[SimplePropertyMsg]
    def __init__(self, param1: _Optional[int] = ..., param2: _Optional[int] = ..., param3: _Optional[str] = ..., property: _Optional[_Iterable[_Union[SimplePropertyMsg, _Mapping]]] = ...) -> None: ...

class SimplePropertyMsg(_message.Message):
    __slots__ = ("param1", "param2", "param3", "param4", "param5", "param6", "param7", "param8", "param9", "param10", "param11", "param12")
    PARAM1_FIELD_NUMBER: _ClassVar[int]
    PARAM2_FIELD_NUMBER: _ClassVar[int]
    PARAM3_FIELD_NUMBER: _ClassVar[int]
    PARAM4_FIELD_NUMBER: _ClassVar[int]
    PARAM5_FIELD_NUMBER: _ClassVar[int]
    PARAM6_FIELD_NUMBER: _ClassVar[int]
    PARAM7_FIELD_NUMBER: _ClassVar[int]
    PARAM8_FIELD_NUMBER: _ClassVar[int]
    PARAM9_FIELD_NUMBER: _ClassVar[int]
    PARAM10_FIELD_NUMBER: _ClassVar[int]
    PARAM11_FIELD_NUMBER: _ClassVar[int]
    PARAM12_FIELD_NUMBER: _ClassVar[int]
    param1: int
    param2: int
    param3: int
    param4: str
    param5: str
    param6: str
    param7: bool
    param8: bool
    param9: bool
    param10: int
    param11: int
    param12: str
    def __init__(self, param1: _Optional[int] = ..., param2: _Optional[int] = ..., param3: _Optional[int] = ..., param4: _Optional[str] = ..., param5: _Optional[str] = ..., param6: _Optional[str] = ..., param7: _Optional[bool] = ..., param8: _Optional[bool] = ..., param9: _Optional[bool] = ..., param10: _Optional[int] = ..., param11: _Optional[int] = ..., param12: _Optional[str] = ...) -> None: ...

class SimpleStarInfoMsg(_message.Message):
    __slots__ = ("id", "templateId", "objectId", "pos", "bagType", "grade", "gp")
    ID_FIELD_NUMBER: _ClassVar[int]
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    OBJECTID_FIELD_NUMBER: _ClassVar[int]
    POS_FIELD_NUMBER: _ClassVar[int]
    BAGTYPE_FIELD_NUMBER: _ClassVar[int]
    GRADE_FIELD_NUMBER: _ClassVar[int]
    GP_FIELD_NUMBER: _ClassVar[int]
    id: int
    templateId: int
    objectId: int
    pos: int
    bagType: int
    grade: int
    gp: int
    def __init__(self, id: _Optional[int] = ..., templateId: _Optional[int] = ..., objectId: _Optional[int] = ..., pos: _Optional[int] = ..., bagType: _Optional[int] = ..., grade: _Optional[int] = ..., gp: _Optional[int] = ...) -> None: ...

class SimpleTaskMsg(_message.Message):
    __slots__ = ("taskId", "isComplete")
    TASKID_FIELD_NUMBER: _ClassVar[int]
    ISCOMPLETE_FIELD_NUMBER: _ClassVar[int]
    taskId: int
    isComplete: int
    def __init__(self, taskId: _Optional[int] = ..., isComplete: _Optional[int] = ...) -> None: ...

class SimpleWatchMsg(_message.Message):
    __slots__ = ("gridType", "gridPos", "jion1", "jion2", "jion3", "jion4")
    GRIDTYPE_FIELD_NUMBER: _ClassVar[int]
    GRIDPOS_FIELD_NUMBER: _ClassVar[int]
    JION1_FIELD_NUMBER: _ClassVar[int]
    JION2_FIELD_NUMBER: _ClassVar[int]
    JION3_FIELD_NUMBER: _ClassVar[int]
    JION4_FIELD_NUMBER: _ClassVar[int]
    gridType: int
    gridPos: int
    jion1: int
    jion2: int
    jion3: int
    jion4: int
    def __init__(self, gridType: _Optional[int] = ..., gridPos: _Optional[int] = ..., jion1: _Optional[int] = ..., jion2: _Optional[int] = ..., jion3: _Optional[int] = ..., jion4: _Optional[int] = ...) -> None: ...

class SingleDayMsg(_message.Message):
    __slots__ = ("day", "getReward", "simpleTask")
    DAY_FIELD_NUMBER: _ClassVar[int]
    GETREWARD_FIELD_NUMBER: _ClassVar[int]
    SIMPLETASK_FIELD_NUMBER: _ClassVar[int]
    day: int
    getReward: int
    simpleTask: _containers.RepeatedCompositeFieldContainer[SimpleTaskMsg]
    def __init__(self, day: _Optional[int] = ..., getReward: _Optional[int] = ..., simpleTask: _Optional[_Iterable[_Union[SimpleTaskMsg, _Mapping]]] = ...) -> None: ...

class SinglePassMsg(_message.Message):
    __slots__ = ("userId", "area", "maxIndex", "areaReward", "rankInfo", "count", "itemCount")
    USERID_FIELD_NUMBER: _ClassVar[int]
    AREA_FIELD_NUMBER: _ClassVar[int]
    MAXINDEX_FIELD_NUMBER: _ClassVar[int]
    AREAREWARD_FIELD_NUMBER: _ClassVar[int]
    RANKINFO_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    ITEMCOUNT_FIELD_NUMBER: _ClassVar[int]
    userId: int
    area: int
    maxIndex: int
    areaReward: str
    rankInfo: _containers.RepeatedCompositeFieldContainer[RankInfoMsg]
    count: int
    itemCount: int
    def __init__(self, userId: _Optional[int] = ..., area: _Optional[int] = ..., maxIndex: _Optional[int] = ..., areaReward: _Optional[str] = ..., rankInfo: _Optional[_Iterable[_Union[RankInfoMsg, _Mapping]]] = ..., count: _Optional[int] = ..., itemCount: _Optional[int] = ...) -> None: ...

class Singlefightadd(_message.Message):
    __slots__ = ("op", "userid", "campType", "add")
    OP_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    CAMPTYPE_FIELD_NUMBER: _ClassVar[int]
    ADD_FIELD_NUMBER: _ClassVar[int]
    op: int
    userid: int
    campType: int
    add: int
    def __init__(self, op: _Optional[int] = ..., userid: _Optional[int] = ..., campType: _Optional[int] = ..., add: _Optional[int] = ...) -> None: ...

class SlotActiveMsg(_message.Message):
    __slots__ = ("open", "op", "status", "slot", "type", "rewarditemtemplateid", "findcost")
    OPEN_FIELD_NUMBER: _ClassVar[int]
    OP_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    SLOT_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    REWARDITEMTEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    FINDCOST_FIELD_NUMBER: _ClassVar[int]
    open: bool
    op: int
    status: int
    slot: str
    type: int
    rewarditemtemplateid: int
    findcost: int
    def __init__(self, open: _Optional[bool] = ..., op: _Optional[int] = ..., status: _Optional[int] = ..., slot: _Optional[str] = ..., type: _Optional[int] = ..., rewarditemtemplateid: _Optional[int] = ..., findcost: _Optional[int] = ...) -> None: ...

class SlotActiveRequest(_message.Message):
    __slots__ = ("op",)
    OP_FIELD_NUMBER: _ClassVar[int]
    op: int
    def __init__(self, op: _Optional[int] = ...) -> None: ...

class SmallMapFogListMsg(_message.Message):
    __slots__ = ("fog",)
    FOG_FIELD_NUMBER: _ClassVar[int]
    fog: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, fog: _Optional[_Iterable[int]] = ...) -> None: ...

class SmithFreshReplaceRspMsg(_message.Message):
    __slots__ = ("result",)
    RESULT_FIELD_NUMBER: _ClassVar[int]
    result: bool
    def __init__(self, result: _Optional[bool] = ...) -> None: ...

class SmithFreshReqMsg(_message.Message):
    __slots__ = ("lock", "bindType", "payType")
    LOCK_FIELD_NUMBER: _ClassVar[int]
    BINDTYPE_FIELD_NUMBER: _ClassVar[int]
    PAYTYPE_FIELD_NUMBER: _ClassVar[int]
    lock: _containers.RepeatedScalarFieldContainer[bool]
    bindType: int
    payType: int
    def __init__(self, lock: _Optional[_Iterable[bool]] = ..., bindType: _Optional[int] = ..., payType: _Optional[int] = ...) -> None: ...

class SmithFreshRspMsg(_message.Message):
    __slots__ = ("randomSkill",)
    RANDOMSKILL_FIELD_NUMBER: _ClassVar[int]
    randomSkill: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, randomSkill: _Optional[_Iterable[int]] = ...) -> None: ...

class SmithResolveRspMsg(_message.Message):
    __slots__ = ("result",)
    RESULT_FIELD_NUMBER: _ClassVar[int]
    result: bool
    def __init__(self, result: _Optional[bool] = ...) -> None: ...

class SmithTransformRspMsg(_message.Message):
    __slots__ = ("result",)
    RESULT_FIELD_NUMBER: _ClassVar[int]
    result: bool
    def __init__(self, result: _Optional[bool] = ...) -> None: ...

class SnsRspMsg(_message.Message):
    __slots__ = ("type", "data", "md5")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    MD5_FIELD_NUMBER: _ClassVar[int]
    type: int
    data: str
    md5: str
    def __init__(self, type: _Optional[int] = ..., data: _Optional[str] = ..., md5: _Optional[str] = ...) -> None: ...

class SoldierMsg(_message.Message):
    __slots__ = ("livingId", "tempId", "type", "side", "pos", "initHp", "hp", "qteTime", "castTime", "armyPawnId", "grade", "phyAttack", "phyDefence", "magAttack", "magDefence", "forceHit", "parry", "sites", "skillId", "attackWound", "hitWound")
    LIVINGID_FIELD_NUMBER: _ClassVar[int]
    TEMPID_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    SIDE_FIELD_NUMBER: _ClassVar[int]
    POS_FIELD_NUMBER: _ClassVar[int]
    INITHP_FIELD_NUMBER: _ClassVar[int]
    HP_FIELD_NUMBER: _ClassVar[int]
    QTETIME_FIELD_NUMBER: _ClassVar[int]
    CASTTIME_FIELD_NUMBER: _ClassVar[int]
    ARMYPAWNID_FIELD_NUMBER: _ClassVar[int]
    GRADE_FIELD_NUMBER: _ClassVar[int]
    PHYATTACK_FIELD_NUMBER: _ClassVar[int]
    PHYDEFENCE_FIELD_NUMBER: _ClassVar[int]
    MAGATTACK_FIELD_NUMBER: _ClassVar[int]
    MAGDEFENCE_FIELD_NUMBER: _ClassVar[int]
    FORCEHIT_FIELD_NUMBER: _ClassVar[int]
    PARRY_FIELD_NUMBER: _ClassVar[int]
    SITES_FIELD_NUMBER: _ClassVar[int]
    SKILLID_FIELD_NUMBER: _ClassVar[int]
    ATTACKWOUND_FIELD_NUMBER: _ClassVar[int]
    HITWOUND_FIELD_NUMBER: _ClassVar[int]
    livingId: int
    tempId: int
    type: int
    side: int
    pos: int
    initHp: int
    hp: int
    qteTime: int
    castTime: int
    armyPawnId: int
    grade: int
    phyAttack: int
    phyDefence: int
    magAttack: int
    magDefence: int
    forceHit: int
    parry: int
    sites: int
    skillId: _containers.RepeatedScalarFieldContainer[int]
    attackWound: int
    hitWound: int
    def __init__(self, livingId: _Optional[int] = ..., tempId: _Optional[int] = ..., type: _Optional[int] = ..., side: _Optional[int] = ..., pos: _Optional[int] = ..., initHp: _Optional[int] = ..., hp: _Optional[int] = ..., qteTime: _Optional[int] = ..., castTime: _Optional[int] = ..., armyPawnId: _Optional[int] = ..., grade: _Optional[int] = ..., phyAttack: _Optional[int] = ..., phyDefence: _Optional[int] = ..., magAttack: _Optional[int] = ..., magDefence: _Optional[int] = ..., forceHit: _Optional[int] = ..., parry: _Optional[int] = ..., sites: _Optional[int] = ..., skillId: _Optional[_Iterable[int]] = ..., attackWound: _Optional[int] = ..., hitWound: _Optional[int] = ...) -> None: ...

class SpacePlayerArmyInfoReqMsg(_message.Message):
    __slots__ = ("userList",)
    USERLIST_FIELD_NUMBER: _ClassVar[int]
    userList: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, userList: _Optional[_Iterable[int]] = ...) -> None: ...

class SpacePlayerMoveMsg(_message.Message):
    __slots__ = ("players",)
    PLAYERS_FIELD_NUMBER: _ClassVar[int]
    players: _containers.RepeatedCompositeFieldContainer[SpacePlayerMsg]
    def __init__(self, players: _Optional[_Iterable[_Union[SpacePlayerMsg, _Mapping]]] = ...) -> None: ...

class SpacePlayerMsg(_message.Message):
    __slots__ = ("playerId", "state", "path")
    PLAYERID_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    PATH_FIELD_NUMBER: _ClassVar[int]
    playerId: int
    state: int
    path: _containers.RepeatedCompositeFieldContainer[PosMsg]
    def __init__(self, playerId: _Optional[int] = ..., state: _Optional[int] = ..., path: _Optional[_Iterable[_Union[PosMsg, _Mapping]]] = ...) -> None: ...

class StandPosMsg(_message.Message):
    __slots__ = ("id", "posX", "posY", "serverName")
    ID_FIELD_NUMBER: _ClassVar[int]
    POSX_FIELD_NUMBER: _ClassVar[int]
    POSY_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    id: int
    posX: int
    posY: int
    serverName: str
    def __init__(self, id: _Optional[int] = ..., posX: _Optional[int] = ..., posY: _Optional[int] = ..., serverName: _Optional[str] = ...) -> None: ...

class StarBufferMsg(_message.Message):
    __slots__ = ("skillId", "level")
    SKILLID_FIELD_NUMBER: _ClassVar[int]
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    skillId: int
    level: int
    def __init__(self, skillId: _Optional[int] = ..., level: _Optional[int] = ...) -> None: ...

class StarComposeReqMsg(_message.Message):
    __slots__ = ("pos", "bagType")
    POS_FIELD_NUMBER: _ClassVar[int]
    BAGTYPE_FIELD_NUMBER: _ClassVar[int]
    pos: int
    bagType: int
    def __init__(self, pos: _Optional[int] = ..., bagType: _Optional[int] = ...) -> None: ...

class StarInfoMsg(_message.Message):
    __slots__ = ("id", "templateId", "userId", "objectId", "pos", "exist", "bagType", "grade", "gp", "isLock")
    ID_FIELD_NUMBER: _ClassVar[int]
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    OBJECTID_FIELD_NUMBER: _ClassVar[int]
    POS_FIELD_NUMBER: _ClassVar[int]
    EXIST_FIELD_NUMBER: _ClassVar[int]
    BAGTYPE_FIELD_NUMBER: _ClassVar[int]
    GRADE_FIELD_NUMBER: _ClassVar[int]
    GP_FIELD_NUMBER: _ClassVar[int]
    ISLOCK_FIELD_NUMBER: _ClassVar[int]
    id: int
    templateId: int
    userId: int
    objectId: int
    pos: int
    exist: bool
    bagType: int
    grade: int
    gp: int
    isLock: bool
    def __init__(self, id: _Optional[int] = ..., templateId: _Optional[int] = ..., userId: _Optional[int] = ..., objectId: _Optional[int] = ..., pos: _Optional[int] = ..., exist: _Optional[bool] = ..., bagType: _Optional[int] = ..., grade: _Optional[int] = ..., gp: _Optional[int] = ..., isLock: _Optional[bool] = ...) -> None: ...

class StarLockReqMsg(_message.Message):
    __slots__ = ("starType", "pos")
    STARTYPE_FIELD_NUMBER: _ClassVar[int]
    POS_FIELD_NUMBER: _ClassVar[int]
    starType: int
    pos: int
    def __init__(self, starType: _Optional[int] = ..., pos: _Optional[int] = ...) -> None: ...

class StarMoveMsg(_message.Message):
    __slots__ = ("changeType", "changePos", "star_Info")
    CHANGETYPE_FIELD_NUMBER: _ClassVar[int]
    CHANGEPOS_FIELD_NUMBER: _ClassVar[int]
    STAR_INFO_FIELD_NUMBER: _ClassVar[int]
    changeType: int
    changePos: int
    star_Info: StarInfoMsg
    def __init__(self, changeType: _Optional[int] = ..., changePos: _Optional[int] = ..., star_Info: _Optional[_Union[StarInfoMsg, _Mapping]] = ...) -> None: ...

class StarMoveReqMsg(_message.Message):
    __slots__ = ("beginStarType", "beginPos", "endStarType", "endPos", "count", "eat")
    BEGINSTARTYPE_FIELD_NUMBER: _ClassVar[int]
    BEGINPOS_FIELD_NUMBER: _ClassVar[int]
    ENDSTARTYPE_FIELD_NUMBER: _ClassVar[int]
    ENDPOS_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    EAT_FIELD_NUMBER: _ClassVar[int]
    beginStarType: int
    beginPos: int
    endStarType: int
    endPos: int
    count: int
    eat: bool
    def __init__(self, beginStarType: _Optional[int] = ..., beginPos: _Optional[int] = ..., endStarType: _Optional[int] = ..., endPos: _Optional[int] = ..., count: _Optional[int] = ..., eat: _Optional[bool] = ...) -> None: ...

class StarMoveRspMsg(_message.Message):
    __slots__ = ("move",)
    MOVE_FIELD_NUMBER: _ClassVar[int]
    move: _containers.RepeatedCompositeFieldContainer[StarMoveMsg]
    def __init__(self, move: _Optional[_Iterable[_Union[StarMoveMsg, _Mapping]]] = ...) -> None: ...

class StarPickReqMsg(_message.Message):
    __slots__ = ("dropsite", "way")
    DROPSITE_FIELD_NUMBER: _ClassVar[int]
    WAY_FIELD_NUMBER: _ClassVar[int]
    dropsite: int
    way: int
    def __init__(self, dropsite: _Optional[int] = ..., way: _Optional[int] = ...) -> None: ...

class StarRandMsg(_message.Message):
    __slots__ = ("dropSite", "starInfo")
    DROPSITE_FIELD_NUMBER: _ClassVar[int]
    STARINFO_FIELD_NUMBER: _ClassVar[int]
    dropSite: int
    starInfo: StarInfoMsg
    def __init__(self, dropSite: _Optional[int] = ..., starInfo: _Optional[_Union[StarInfoMsg, _Mapping]] = ...) -> None: ...

class StarRandReqMsg(_message.Message):
    __slots__ = ("site",)
    SITE_FIELD_NUMBER: _ClassVar[int]
    site: int
    def __init__(self, site: _Optional[int] = ...) -> None: ...

class StarRandRspMsg(_message.Message):
    __slots__ = ("starRand", "site")
    STARRAND_FIELD_NUMBER: _ClassVar[int]
    SITE_FIELD_NUMBER: _ClassVar[int]
    starRand: _containers.RepeatedCompositeFieldContainer[StarRandMsg]
    site: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, starRand: _Optional[_Iterable[_Union[StarRandMsg, _Mapping]]] = ..., site: _Optional[_Iterable[int]] = ...) -> None: ...

class StarShopMsg(_message.Message):
    __slots__ = ("goodId", "result")
    GOODID_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    goodId: int
    result: int
    def __init__(self, goodId: _Optional[int] = ..., result: _Optional[int] = ...) -> None: ...

class StoreReqMsg(_message.Message):
    __slots__ = ("holePos", "operate", "bagType", "bagPos", "mountPos", "composeId", "composeNum", "autoBuy", "srcItemid", "desItemid", "count", "payType")
    HOLEPOS_FIELD_NUMBER: _ClassVar[int]
    OPERATE_FIELD_NUMBER: _ClassVar[int]
    BAGTYPE_FIELD_NUMBER: _ClassVar[int]
    BAGPOS_FIELD_NUMBER: _ClassVar[int]
    MOUNTPOS_FIELD_NUMBER: _ClassVar[int]
    COMPOSEID_FIELD_NUMBER: _ClassVar[int]
    COMPOSENUM_FIELD_NUMBER: _ClassVar[int]
    AUTOBUY_FIELD_NUMBER: _ClassVar[int]
    SRCITEMID_FIELD_NUMBER: _ClassVar[int]
    DESITEMID_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    PAYTYPE_FIELD_NUMBER: _ClassVar[int]
    holePos: int
    operate: bool
    bagType: int
    bagPos: int
    mountPos: int
    composeId: int
    composeNum: int
    autoBuy: bool
    srcItemid: int
    desItemid: int
    count: int
    payType: int
    def __init__(self, holePos: _Optional[int] = ..., operate: _Optional[bool] = ..., bagType: _Optional[int] = ..., bagPos: _Optional[int] = ..., mountPos: _Optional[int] = ..., composeId: _Optional[int] = ..., composeNum: _Optional[int] = ..., autoBuy: _Optional[bool] = ..., srcItemid: _Optional[int] = ..., desItemid: _Optional[int] = ..., count: _Optional[int] = ..., payType: _Optional[int] = ...) -> None: ...

class StoreRspMsg(_message.Message):
    __slots__ = ("composeResult", "composeTemplateId", "strengResult", "strengthenGrade", "pos", "objectId", "bagType")
    COMPOSERESULT_FIELD_NUMBER: _ClassVar[int]
    COMPOSETEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    STRENGRESULT_FIELD_NUMBER: _ClassVar[int]
    STRENGTHENGRADE_FIELD_NUMBER: _ClassVar[int]
    POS_FIELD_NUMBER: _ClassVar[int]
    OBJECTID_FIELD_NUMBER: _ClassVar[int]
    BAGTYPE_FIELD_NUMBER: _ClassVar[int]
    composeResult: bool
    composeTemplateId: int
    strengResult: bool
    strengthenGrade: int
    pos: int
    objectId: int
    bagType: int
    def __init__(self, composeResult: _Optional[bool] = ..., composeTemplateId: _Optional[int] = ..., strengResult: _Optional[bool] = ..., strengthenGrade: _Optional[int] = ..., pos: _Optional[int] = ..., objectId: _Optional[int] = ..., bagType: _Optional[int] = ...) -> None: ...

class SumActiveDataMsg(_message.Message):
    __slots__ = ("datas",)
    DATAS_FIELD_NUMBER: _ClassVar[int]
    datas: _containers.RepeatedCompositeFieldContainer[ActiveData]
    def __init__(self, datas: _Optional[_Iterable[_Union[ActiveData, _Mapping]]] = ...) -> None: ...

class SumActiveGetPackageMsg(_message.Message):
    __slots__ = ("activeId", "packageId", "type", "count")
    ACTIVEID_FIELD_NUMBER: _ClassVar[int]
    PACKAGEID_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    activeId: str
    packageId: str
    type: int
    count: int
    def __init__(self, activeId: _Optional[str] = ..., packageId: _Optional[str] = ..., type: _Optional[int] = ..., count: _Optional[int] = ...) -> None: ...

class SumActiveItemInfoMsg(_message.Message):
    __slots__ = ("templateId", "templateType", "count", "isbind", "length", "job")
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    TEMPLATETYPE_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    ISBIND_FIELD_NUMBER: _ClassVar[int]
    LENGTH_FIELD_NUMBER: _ClassVar[int]
    JOB_FIELD_NUMBER: _ClassVar[int]
    templateId: int
    templateType: int
    count: int
    isbind: bool
    length: int
    job: int
    def __init__(self, templateId: _Optional[int] = ..., templateType: _Optional[int] = ..., count: _Optional[int] = ..., isbind: _Optional[bool] = ..., length: _Optional[int] = ..., job: _Optional[int] = ...) -> None: ...

class SumActivePackageMsg(_message.Message):
    __slots__ = ("packageId", "order", "items", "conditions")
    PACKAGEID_FIELD_NUMBER: _ClassVar[int]
    ORDER_FIELD_NUMBER: _ClassVar[int]
    ITEMS_FIELD_NUMBER: _ClassVar[int]
    CONDITIONS_FIELD_NUMBER: _ClassVar[int]
    packageId: str
    order: int
    items: _containers.RepeatedCompositeFieldContainer[SumActiveItemInfoMsg]
    conditions: _containers.RepeatedCompositeFieldContainer[PackageConditionMsg]
    def __init__(self, packageId: _Optional[str] = ..., order: _Optional[int] = ..., items: _Optional[_Iterable[_Union[SumActiveItemInfoMsg, _Mapping]]] = ..., conditions: _Optional[_Iterable[_Union[PackageConditionMsg, _Mapping]]] = ...) -> None: ...

class SumActiveinfoMsg(_message.Message):
    __slots__ = ("activeId", "beginDate", "endDate", "title", "detail", "conditionDetail", "getway", "packages", "activeType", "startTime", "stopTime", "order", "appendParam", "isInitiate")
    ACTIVEID_FIELD_NUMBER: _ClassVar[int]
    BEGINDATE_FIELD_NUMBER: _ClassVar[int]
    ENDDATE_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    DETAIL_FIELD_NUMBER: _ClassVar[int]
    CONDITIONDETAIL_FIELD_NUMBER: _ClassVar[int]
    GETWAY_FIELD_NUMBER: _ClassVar[int]
    PACKAGES_FIELD_NUMBER: _ClassVar[int]
    ACTIVETYPE_FIELD_NUMBER: _ClassVar[int]
    STARTTIME_FIELD_NUMBER: _ClassVar[int]
    STOPTIME_FIELD_NUMBER: _ClassVar[int]
    ORDER_FIELD_NUMBER: _ClassVar[int]
    APPENDPARAM_FIELD_NUMBER: _ClassVar[int]
    ISINITIATE_FIELD_NUMBER: _ClassVar[int]
    activeId: str
    beginDate: str
    endDate: str
    title: str
    detail: str
    conditionDetail: str
    getway: int
    packages: _containers.RepeatedCompositeFieldContainer[SumActivePackageMsg]
    activeType: int
    startTime: str
    stopTime: str
    order: int
    appendParam: str
    isInitiate: int
    def __init__(self, activeId: _Optional[str] = ..., beginDate: _Optional[str] = ..., endDate: _Optional[str] = ..., title: _Optional[str] = ..., detail: _Optional[str] = ..., conditionDetail: _Optional[str] = ..., getway: _Optional[int] = ..., packages: _Optional[_Iterable[_Union[SumActivePackageMsg, _Mapping]]] = ..., activeType: _Optional[int] = ..., startTime: _Optional[str] = ..., stopTime: _Optional[str] = ..., order: _Optional[int] = ..., appendParam: _Optional[str] = ..., isInitiate: _Optional[int] = ...) -> None: ...

class SumActivesMsg(_message.Message):
    __slots__ = ("actives", "dataStamp", "curPage", "maxPage")
    ACTIVES_FIELD_NUMBER: _ClassVar[int]
    DATASTAMP_FIELD_NUMBER: _ClassVar[int]
    CURPAGE_FIELD_NUMBER: _ClassVar[int]
    MAXPAGE_FIELD_NUMBER: _ClassVar[int]
    actives: _containers.RepeatedCompositeFieldContainer[SumActiveinfoMsg]
    dataStamp: int
    curPage: int
    maxPage: int
    def __init__(self, actives: _Optional[_Iterable[_Union[SumActiveinfoMsg, _Mapping]]] = ..., dataStamp: _Optional[int] = ..., curPage: _Optional[int] = ..., maxPage: _Optional[int] = ...) -> None: ...

class SuperSigninCardReqMsg(_message.Message):
    __slots__ = ("opType", "date")
    OPTYPE_FIELD_NUMBER: _ClassVar[int]
    DATE_FIELD_NUMBER: _ClassVar[int]
    opType: int
    date: int
    def __init__(self, opType: _Optional[int] = ..., date: _Optional[int] = ...) -> None: ...

class SuperSigninCardRespMsg(_message.Message):
    __slots__ = ("details",)
    DETAILS_FIELD_NUMBER: _ClassVar[int]
    details: _containers.RepeatedCompositeFieldContainer[SuperSigninDetailMsg]
    def __init__(self, details: _Optional[_Iterable[_Union[SuperSigninDetailMsg, _Mapping]]] = ...) -> None: ...

class SuperSigninDetailMsg(_message.Message):
    __slots__ = ("date", "state")
    DATE_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    date: int
    state: int
    def __init__(self, date: _Optional[int] = ..., state: _Optional[int] = ...) -> None: ...

class SuperSigninRewardMsg(_message.Message):
    __slots__ = ("cardPrice", "reSigninPrice", "temp")
    CARDPRICE_FIELD_NUMBER: _ClassVar[int]
    RESIGNINPRICE_FIELD_NUMBER: _ClassVar[int]
    TEMP_FIELD_NUMBER: _ClassVar[int]
    cardPrice: int
    reSigninPrice: int
    temp: _containers.RepeatedCompositeFieldContainer[SuperSigninTempMsg]
    def __init__(self, cardPrice: _Optional[int] = ..., reSigninPrice: _Optional[int] = ..., temp: _Optional[_Iterable[_Union[SuperSigninTempMsg, _Mapping]]] = ...) -> None: ...

class SuperSigninTempMsg(_message.Message):
    __slots__ = ("date", "itemMsg")
    DATE_FIELD_NUMBER: _ClassVar[int]
    ITEMMSG_FIELD_NUMBER: _ClassVar[int]
    date: int
    itemMsg: str
    def __init__(self, date: _Optional[int] = ..., itemMsg: _Optional[str] = ...) -> None: ...

class SweepResult(_message.Message):
    __slots__ = ("type", "gold", "gp", "campaignId", "time", "items", "cIndex", "eIndex", "finishCount", "count", "mailIn")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    GOLD_FIELD_NUMBER: _ClassVar[int]
    GP_FIELD_NUMBER: _ClassVar[int]
    CAMPAIGNID_FIELD_NUMBER: _ClassVar[int]
    TIME_FIELD_NUMBER: _ClassVar[int]
    ITEMS_FIELD_NUMBER: _ClassVar[int]
    CINDEX_FIELD_NUMBER: _ClassVar[int]
    EINDEX_FIELD_NUMBER: _ClassVar[int]
    FINISHCOUNT_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    MAILIN_FIELD_NUMBER: _ClassVar[int]
    type: int
    gold: int
    gp: int
    campaignId: int
    time: int
    items: _containers.RepeatedCompositeFieldContainer[ItemTemplate]
    cIndex: int
    eIndex: int
    finishCount: int
    count: int
    mailIn: int
    def __init__(self, type: _Optional[int] = ..., gold: _Optional[int] = ..., gp: _Optional[int] = ..., campaignId: _Optional[int] = ..., time: _Optional[int] = ..., items: _Optional[_Iterable[_Union[ItemTemplate, _Mapping]]] = ..., cIndex: _Optional[int] = ..., eIndex: _Optional[int] = ..., finishCount: _Optional[int] = ..., count: _Optional[int] = ..., mailIn: _Optional[int] = ...) -> None: ...

class SwitchInfoListMsg(_message.Message):
    __slots__ = ("switches",)
    SWITCHES_FIELD_NUMBER: _ClassVar[int]
    switches: _containers.RepeatedCompositeFieldContainer[SwitchInfoMsg]
    def __init__(self, switches: _Optional[_Iterable[_Union[SwitchInfoMsg, _Mapping]]] = ...) -> None: ...

class SwitchInfoMsg(_message.Message):
    __slots__ = ("switchId", "switchType", "isOpen", "beginDate", "endDate")
    SWITCHID_FIELD_NUMBER: _ClassVar[int]
    SWITCHTYPE_FIELD_NUMBER: _ClassVar[int]
    ISOPEN_FIELD_NUMBER: _ClassVar[int]
    BEGINDATE_FIELD_NUMBER: _ClassVar[int]
    ENDDATE_FIELD_NUMBER: _ClassVar[int]
    switchId: int
    switchType: int
    isOpen: bool
    beginDate: str
    endDate: str
    def __init__(self, switchId: _Optional[int] = ..., switchType: _Optional[int] = ..., isOpen: _Optional[bool] = ..., beginDate: _Optional[str] = ..., endDate: _Optional[str] = ...) -> None: ...

class SynchronizedTimeMsg(_message.Message):
    __slots__ = ("sysCurtime", "sysMillisecond")
    SYSCURTIME_FIELD_NUMBER: _ClassVar[int]
    SYSMILLISECOND_FIELD_NUMBER: _ClassVar[int]
    sysCurtime: str
    sysMillisecond: int
    def __init__(self, sysCurtime: _Optional[str] = ..., sysMillisecond: _Optional[int] = ...) -> None: ...

class SysAnswerQuestionStateMsg(_message.Message):
    __slots__ = ("sysState", "sysAnswerCount", "leftCount", "beginDate", "lastDate")
    SYSSTATE_FIELD_NUMBER: _ClassVar[int]
    SYSANSWERCOUNT_FIELD_NUMBER: _ClassVar[int]
    LEFTCOUNT_FIELD_NUMBER: _ClassVar[int]
    BEGINDATE_FIELD_NUMBER: _ClassVar[int]
    LASTDATE_FIELD_NUMBER: _ClassVar[int]
    sysState: int
    sysAnswerCount: int
    leftCount: int
    beginDate: str
    lastDate: str
    def __init__(self, sysState: _Optional[int] = ..., sysAnswerCount: _Optional[int] = ..., leftCount: _Optional[int] = ..., beginDate: _Optional[str] = ..., lastDate: _Optional[str] = ...) -> None: ...

class SystemArmyMsg(_message.Message):
    __slots__ = ("heroTemplated", "soldierTemplated")
    HEROTEMPLATED_FIELD_NUMBER: _ClassVar[int]
    SOLDIERTEMPLATED_FIELD_NUMBER: _ClassVar[int]
    heroTemplated: _containers.RepeatedScalarFieldContainer[int]
    soldierTemplated: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, heroTemplated: _Optional[_Iterable[int]] = ..., soldierTemplated: _Optional[_Iterable[int]] = ...) -> None: ...

class SystemPropertyMsg(_message.Message):
    __slots__ = ("sysCurtime", "sysStarTime", "sysMillisecond")
    SYSCURTIME_FIELD_NUMBER: _ClassVar[int]
    SYSSTARTIME_FIELD_NUMBER: _ClassVar[int]
    SYSMILLISECOND_FIELD_NUMBER: _ClassVar[int]
    sysCurtime: str
    sysStarTime: str
    sysMillisecond: int
    def __init__(self, sysCurtime: _Optional[str] = ..., sysStarTime: _Optional[str] = ..., sysMillisecond: _Optional[int] = ...) -> None: ...

class TakeLoginReward(_message.Message):
    __slots__ = ("index",)
    INDEX_FIELD_NUMBER: _ClassVar[int]
    index: int
    def __init__(self, index: _Optional[int] = ...) -> None: ...

class TalentUpGradeMsg(_message.Message):
    __slots__ = ("upresult",)
    UPRESULT_FIELD_NUMBER: _ClassVar[int]
    upresult: bool
    def __init__(self, upresult: _Optional[bool] = ...) -> None: ...

class TaskCampaignReqMsg(_message.Message):
    __slots__ = ("dungeonId", "campaignId")
    DUNGEONID_FIELD_NUMBER: _ClassVar[int]
    CAMPAIGNID_FIELD_NUMBER: _ClassVar[int]
    dungeonId: int
    campaignId: int
    def __init__(self, dungeonId: _Optional[int] = ..., campaignId: _Optional[int] = ...) -> None: ...

class TeamEditMsg(_message.Message):
    __slots__ = ("userId", "op", "param1", "param2")
    USERID_FIELD_NUMBER: _ClassVar[int]
    OP_FIELD_NUMBER: _ClassVar[int]
    PARAM1_FIELD_NUMBER: _ClassVar[int]
    PARAM2_FIELD_NUMBER: _ClassVar[int]
    userId: int
    op: int
    param1: int
    param2: int
    def __init__(self, userId: _Optional[int] = ..., op: _Optional[int] = ..., param1: _Optional[int] = ..., param2: _Optional[int] = ...) -> None: ...

class TeamInfoMsg(_message.Message):
    __slots__ = ("teamId", "memberId", "captainId", "memberDetail")
    TEAMID_FIELD_NUMBER: _ClassVar[int]
    MEMBERID_FIELD_NUMBER: _ClassVar[int]
    CAPTAINID_FIELD_NUMBER: _ClassVar[int]
    MEMBERDETAIL_FIELD_NUMBER: _ClassVar[int]
    teamId: int
    memberId: _containers.RepeatedScalarFieldContainer[int]
    captainId: int
    memberDetail: _containers.RepeatedCompositeFieldContainer[TeamPlayerInfoMsg]
    def __init__(self, teamId: _Optional[int] = ..., memberId: _Optional[_Iterable[int]] = ..., captainId: _Optional[int] = ..., memberDetail: _Optional[_Iterable[_Union[TeamPlayerInfoMsg, _Mapping]]] = ...) -> None: ...

class TeamPlayerInfoMsg(_message.Message):
    __slots__ = ("count", "hasLeftForNow", "heroId", "playerId", "grades", "nickName", "sex", "templateId", "arm", "cloth", "armyId", "fightingCapacity", "curPosX", "curPosY", "campaignId", "onlineState", "consortiaId", "consortiaName", "changeShapeId", "armyState", "teamId", "bufferTempId", "geste", "headId", "isVip", "vipType", "mountTempId", "mountGrade", "wing", "serverName", "hat", "fashionArm", "fashionCloth", "hide", "appellid", "vehicleTemplateId", "fateSkills", "petTemplateId", "petQuqlity", "petName")
    COUNT_FIELD_NUMBER: _ClassVar[int]
    HASLEFTFORNOW_FIELD_NUMBER: _ClassVar[int]
    HEROID_FIELD_NUMBER: _ClassVar[int]
    PLAYERID_FIELD_NUMBER: _ClassVar[int]
    GRADES_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    SEX_FIELD_NUMBER: _ClassVar[int]
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    ARM_FIELD_NUMBER: _ClassVar[int]
    CLOTH_FIELD_NUMBER: _ClassVar[int]
    ARMYID_FIELD_NUMBER: _ClassVar[int]
    FIGHTINGCAPACITY_FIELD_NUMBER: _ClassVar[int]
    CURPOSX_FIELD_NUMBER: _ClassVar[int]
    CURPOSY_FIELD_NUMBER: _ClassVar[int]
    CAMPAIGNID_FIELD_NUMBER: _ClassVar[int]
    ONLINESTATE_FIELD_NUMBER: _ClassVar[int]
    CONSORTIAID_FIELD_NUMBER: _ClassVar[int]
    CONSORTIANAME_FIELD_NUMBER: _ClassVar[int]
    CHANGESHAPEID_FIELD_NUMBER: _ClassVar[int]
    ARMYSTATE_FIELD_NUMBER: _ClassVar[int]
    TEAMID_FIELD_NUMBER: _ClassVar[int]
    BUFFERTEMPID_FIELD_NUMBER: _ClassVar[int]
    GESTE_FIELD_NUMBER: _ClassVar[int]
    HEADID_FIELD_NUMBER: _ClassVar[int]
    ISVIP_FIELD_NUMBER: _ClassVar[int]
    VIPTYPE_FIELD_NUMBER: _ClassVar[int]
    MOUNTTEMPID_FIELD_NUMBER: _ClassVar[int]
    MOUNTGRADE_FIELD_NUMBER: _ClassVar[int]
    WING_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    HAT_FIELD_NUMBER: _ClassVar[int]
    FASHIONARM_FIELD_NUMBER: _ClassVar[int]
    FASHIONCLOTH_FIELD_NUMBER: _ClassVar[int]
    HIDE_FIELD_NUMBER: _ClassVar[int]
    APPELLID_FIELD_NUMBER: _ClassVar[int]
    VEHICLETEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    FATESKILLS_FIELD_NUMBER: _ClassVar[int]
    PETTEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    PETQUQLITY_FIELD_NUMBER: _ClassVar[int]
    PETNAME_FIELD_NUMBER: _ClassVar[int]
    count: int
    hasLeftForNow: bool
    heroId: int
    playerId: int
    grades: int
    nickName: str
    sex: int
    templateId: int
    arm: str
    cloth: str
    armyId: int
    fightingCapacity: int
    curPosX: int
    curPosY: int
    campaignId: int
    onlineState: bool
    consortiaId: int
    consortiaName: str
    changeShapeId: int
    armyState: int
    teamId: int
    bufferTempId: int
    geste: int
    headId: int
    isVip: bool
    vipType: int
    mountTempId: int
    mountGrade: int
    wing: str
    serverName: str
    hat: str
    fashionArm: str
    fashionCloth: str
    hide: bool
    appellid: int
    vehicleTemplateId: int
    fateSkills: str
    petTemplateId: int
    petQuqlity: int
    petName: str
    def __init__(self, count: _Optional[int] = ..., hasLeftForNow: _Optional[bool] = ..., heroId: _Optional[int] = ..., playerId: _Optional[int] = ..., grades: _Optional[int] = ..., nickName: _Optional[str] = ..., sex: _Optional[int] = ..., templateId: _Optional[int] = ..., arm: _Optional[str] = ..., cloth: _Optional[str] = ..., armyId: _Optional[int] = ..., fightingCapacity: _Optional[int] = ..., curPosX: _Optional[int] = ..., curPosY: _Optional[int] = ..., campaignId: _Optional[int] = ..., onlineState: _Optional[bool] = ..., consortiaId: _Optional[int] = ..., consortiaName: _Optional[str] = ..., changeShapeId: _Optional[int] = ..., armyState: _Optional[int] = ..., teamId: _Optional[int] = ..., bufferTempId: _Optional[int] = ..., geste: _Optional[int] = ..., headId: _Optional[int] = ..., isVip: _Optional[bool] = ..., vipType: _Optional[int] = ..., mountTempId: _Optional[int] = ..., mountGrade: _Optional[int] = ..., wing: _Optional[str] = ..., serverName: _Optional[str] = ..., hat: _Optional[str] = ..., fashionArm: _Optional[str] = ..., fashionCloth: _Optional[str] = ..., hide: _Optional[bool] = ..., appellid: _Optional[int] = ..., vehicleTemplateId: _Optional[int] = ..., fateSkills: _Optional[str] = ..., petTemplateId: _Optional[int] = ..., petQuqlity: _Optional[int] = ..., petName: _Optional[str] = ...) -> None: ...

class TenAnswerQuestionOrderMsg(_message.Message):
    __slots__ = ("tenAQ_Info",)
    TENAQ_INFO_FIELD_NUMBER: _ClassVar[int]
    tenAQ_Info: _containers.RepeatedCompositeFieldContainer[answerquestionorderMsg]
    def __init__(self, tenAQ_Info: _Optional[_Iterable[_Union[answerquestionorderMsg, _Mapping]]] = ...) -> None: ...

class TimeJudgeMsg(_message.Message):
    __slots__ = ("isAdd", "secondCount")
    ISADD_FIELD_NUMBER: _ClassVar[int]
    SECONDCOUNT_FIELD_NUMBER: _ClassVar[int]
    isAdd: bool
    secondCount: int
    def __init__(self, isAdd: _Optional[bool] = ..., secondCount: _Optional[int] = ...) -> None: ...

class TimerInfoListMsg(_message.Message):
    __slots__ = ("timerInfo",)
    TIMERINFO_FIELD_NUMBER: _ClassVar[int]
    timerInfo: _containers.RepeatedCompositeFieldContainer[TimerInfoMsg]
    def __init__(self, timerInfo: _Optional[_Iterable[_Union[TimerInfoMsg, _Mapping]]] = ...) -> None: ...

class TimerInfoMsg(_message.Message):
    __slots__ = ("type", "index", "name", "readyOpen", "readyStop", "finalOpen", "finalStop", "param1", "param2", "param3", "signupTime")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    INDEX_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    READYOPEN_FIELD_NUMBER: _ClassVar[int]
    READYSTOP_FIELD_NUMBER: _ClassVar[int]
    FINALOPEN_FIELD_NUMBER: _ClassVar[int]
    FINALSTOP_FIELD_NUMBER: _ClassVar[int]
    PARAM1_FIELD_NUMBER: _ClassVar[int]
    PARAM2_FIELD_NUMBER: _ClassVar[int]
    PARAM3_FIELD_NUMBER: _ClassVar[int]
    SIGNUPTIME_FIELD_NUMBER: _ClassVar[int]
    type: int
    index: int
    name: str
    readyOpen: str
    readyStop: str
    finalOpen: str
    finalStop: str
    param1: str
    param2: str
    param3: str
    signupTime: str
    def __init__(self, type: _Optional[int] = ..., index: _Optional[int] = ..., name: _Optional[str] = ..., readyOpen: _Optional[str] = ..., readyStop: _Optional[str] = ..., finalOpen: _Optional[str] = ..., finalStop: _Optional[str] = ..., param1: _Optional[str] = ..., param2: _Optional[str] = ..., param3: _Optional[str] = ..., signupTime: _Optional[str] = ...) -> None: ...

class TokenInfoMsg(_message.Message):
    __slots__ = ("masterType", "amount", "expiredDate")
    MASTERTYPE_FIELD_NUMBER: _ClassVar[int]
    AMOUNT_FIELD_NUMBER: _ClassVar[int]
    EXPIREDDATE_FIELD_NUMBER: _ClassVar[int]
    masterType: int
    amount: int
    expiredDate: str
    def __init__(self, masterType: _Optional[int] = ..., amount: _Optional[int] = ..., expiredDate: _Optional[str] = ...) -> None: ...

class TollgateChallengeMsg(_message.Message):
    __slots__ = ("tollgateId", "attackUserid", "attackName", "attackTime", "remainTime", "lastHp")
    TOLLGATEID_FIELD_NUMBER: _ClassVar[int]
    ATTACKUSERID_FIELD_NUMBER: _ClassVar[int]
    ATTACKNAME_FIELD_NUMBER: _ClassVar[int]
    ATTACKTIME_FIELD_NUMBER: _ClassVar[int]
    REMAINTIME_FIELD_NUMBER: _ClassVar[int]
    LASTHP_FIELD_NUMBER: _ClassVar[int]
    tollgateId: int
    attackUserid: int
    attackName: str
    attackTime: str
    remainTime: int
    lastHp: int
    def __init__(self, tollgateId: _Optional[int] = ..., attackUserid: _Optional[int] = ..., attackName: _Optional[str] = ..., attackTime: _Optional[str] = ..., remainTime: _Optional[int] = ..., lastHp: _Optional[int] = ...) -> None: ...

class TollgateMsg(_message.Message):
    __slots__ = ("type", "userId", "endTime", "order", "score", "remainCount", "remainTime", "challengeInfo", "scoreInfo", "isOpen", "curTollgateId", "luckyReward", "remainBuyCount", "startTime", "addTimeCount")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    ENDTIME_FIELD_NUMBER: _ClassVar[int]
    ORDER_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    REMAINCOUNT_FIELD_NUMBER: _ClassVar[int]
    REMAINTIME_FIELD_NUMBER: _ClassVar[int]
    CHALLENGEINFO_FIELD_NUMBER: _ClassVar[int]
    SCOREINFO_FIELD_NUMBER: _ClassVar[int]
    ISOPEN_FIELD_NUMBER: _ClassVar[int]
    CURTOLLGATEID_FIELD_NUMBER: _ClassVar[int]
    LUCKYREWARD_FIELD_NUMBER: _ClassVar[int]
    REMAINBUYCOUNT_FIELD_NUMBER: _ClassVar[int]
    STARTTIME_FIELD_NUMBER: _ClassVar[int]
    ADDTIMECOUNT_FIELD_NUMBER: _ClassVar[int]
    type: int
    userId: int
    endTime: str
    order: int
    score: int
    remainCount: int
    remainTime: int
    challengeInfo: _containers.RepeatedCompositeFieldContainer[TollgateChallengeMsg]
    scoreInfo: _containers.RepeatedCompositeFieldContainer[ChallengeScoreMsg]
    isOpen: bool
    curTollgateId: int
    luckyReward: str
    remainBuyCount: int
    startTime: str
    addTimeCount: int
    def __init__(self, type: _Optional[int] = ..., userId: _Optional[int] = ..., endTime: _Optional[str] = ..., order: _Optional[int] = ..., score: _Optional[int] = ..., remainCount: _Optional[int] = ..., remainTime: _Optional[int] = ..., challengeInfo: _Optional[_Iterable[_Union[TollgateChallengeMsg, _Mapping]]] = ..., scoreInfo: _Optional[_Iterable[_Union[ChallengeScoreMsg, _Mapping]]] = ..., isOpen: _Optional[bool] = ..., curTollgateId: _Optional[int] = ..., luckyReward: _Optional[str] = ..., remainBuyCount: _Optional[int] = ..., startTime: _Optional[str] = ..., addTimeCount: _Optional[int] = ...) -> None: ...

class TollgateRewardMsg(_message.Message):
    __slots__ = ("userId", "score", "order", "scoreItems", "luckyItems")
    USERID_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    ORDER_FIELD_NUMBER: _ClassVar[int]
    SCOREITEMS_FIELD_NUMBER: _ClassVar[int]
    LUCKYITEMS_FIELD_NUMBER: _ClassVar[int]
    userId: int
    score: int
    order: int
    scoreItems: str
    luckyItems: str
    def __init__(self, userId: _Optional[int] = ..., score: _Optional[int] = ..., order: _Optional[int] = ..., scoreItems: _Optional[str] = ..., luckyItems: _Optional[str] = ...) -> None: ...

class TowerDiedMsg(_message.Message):
    __slots__ = ("title", "msg")
    TITLE_FIELD_NUMBER: _ClassVar[int]
    MSG_FIELD_NUMBER: _ClassVar[int]
    title: str
    msg: str
    def __init__(self, title: _Optional[str] = ..., msg: _Optional[str] = ...) -> None: ...

class TowerInfoMsg(_message.Message):
    __slots__ = ("enterCount", "totalGp", "towerIndex", "maxIndex", "order", "maxEnterCount", "itemTempIds", "freeEnterCount", "campaignId", "index", "firstHitId", "firstHitName")
    ENTERCOUNT_FIELD_NUMBER: _ClassVar[int]
    TOTALGP_FIELD_NUMBER: _ClassVar[int]
    TOWERINDEX_FIELD_NUMBER: _ClassVar[int]
    MAXINDEX_FIELD_NUMBER: _ClassVar[int]
    ORDER_FIELD_NUMBER: _ClassVar[int]
    MAXENTERCOUNT_FIELD_NUMBER: _ClassVar[int]
    ITEMTEMPIDS_FIELD_NUMBER: _ClassVar[int]
    FREEENTERCOUNT_FIELD_NUMBER: _ClassVar[int]
    CAMPAIGNID_FIELD_NUMBER: _ClassVar[int]
    INDEX_FIELD_NUMBER: _ClassVar[int]
    FIRSTHITID_FIELD_NUMBER: _ClassVar[int]
    FIRSTHITNAME_FIELD_NUMBER: _ClassVar[int]
    enterCount: int
    totalGp: int
    towerIndex: int
    maxIndex: int
    order: int
    maxEnterCount: int
    itemTempIds: str
    freeEnterCount: int
    campaignId: int
    index: int
    firstHitId: int
    firstHitName: str
    def __init__(self, enterCount: _Optional[int] = ..., totalGp: _Optional[int] = ..., towerIndex: _Optional[int] = ..., maxIndex: _Optional[int] = ..., order: _Optional[int] = ..., maxEnterCount: _Optional[int] = ..., itemTempIds: _Optional[str] = ..., freeEnterCount: _Optional[int] = ..., campaignId: _Optional[int] = ..., index: _Optional[int] = ..., firstHitId: _Optional[int] = ..., firstHitName: _Optional[str] = ...) -> None: ...

class TowerInfoReqMsg(_message.Message):
    __slots__ = ("index",)
    INDEX_FIELD_NUMBER: _ClassVar[int]
    index: int
    def __init__(self, index: _Optional[int] = ...) -> None: ...

class TowerListMsg(_message.Message):
    __slots__ = ("towerInfo",)
    TOWERINFO_FIELD_NUMBER: _ClassVar[int]
    towerInfo: _containers.RepeatedCompositeFieldContainer[TowerInfoMsg]
    def __init__(self, towerInfo: _Optional[_Iterable[_Union[TowerInfoMsg, _Mapping]]] = ...) -> None: ...

class TramcarInfoMsg(_message.Message):
    __slots__ = ("carInfo", "userIds", "activeTime", "count", "multiple")
    CARINFO_FIELD_NUMBER: _ClassVar[int]
    USERIDS_FIELD_NUMBER: _ClassVar[int]
    ACTIVETIME_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    MULTIPLE_FIELD_NUMBER: _ClassVar[int]
    carInfo: _containers.RepeatedCompositeFieldContainer[CarInfo]
    userIds: _containers.RepeatedScalarFieldContainer[int]
    activeTime: int
    count: int
    multiple: int
    def __init__(self, carInfo: _Optional[_Iterable[_Union[CarInfo, _Mapping]]] = ..., userIds: _Optional[_Iterable[int]] = ..., activeTime: _Optional[int] = ..., count: _Optional[int] = ..., multiple: _Optional[int] = ...) -> None: ...

class TransInfoMsg(_message.Message):
    __slots__ = ("currentEnergy", "remainTime")
    CURRENTENERGY_FIELD_NUMBER: _ClassVar[int]
    REMAINTIME_FIELD_NUMBER: _ClassVar[int]
    currentEnergy: int
    remainTime: int
    def __init__(self, currentEnergy: _Optional[int] = ..., remainTime: _Optional[int] = ...) -> None: ...

class TreeInfoMsg(_message.Message):
    __slots__ = ("userId", "nickName", "waterCount", "fruitCount", "isFirstFruit", "nextPickTime", "property1", "property2", "lastWaterTime", "leftTime", "leftPickTime")
    USERID_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    WATERCOUNT_FIELD_NUMBER: _ClassVar[int]
    FRUITCOUNT_FIELD_NUMBER: _ClassVar[int]
    ISFIRSTFRUIT_FIELD_NUMBER: _ClassVar[int]
    NEXTPICKTIME_FIELD_NUMBER: _ClassVar[int]
    PROPERTY1_FIELD_NUMBER: _ClassVar[int]
    PROPERTY2_FIELD_NUMBER: _ClassVar[int]
    LASTWATERTIME_FIELD_NUMBER: _ClassVar[int]
    LEFTTIME_FIELD_NUMBER: _ClassVar[int]
    LEFTPICKTIME_FIELD_NUMBER: _ClassVar[int]
    userId: int
    nickName: str
    waterCount: int
    fruitCount: int
    isFirstFruit: bool
    nextPickTime: str
    property1: int
    property2: int
    lastWaterTime: str
    leftTime: int
    leftPickTime: int
    def __init__(self, userId: _Optional[int] = ..., nickName: _Optional[str] = ..., waterCount: _Optional[int] = ..., fruitCount: _Optional[int] = ..., isFirstFruit: _Optional[bool] = ..., nextPickTime: _Optional[str] = ..., property1: _Optional[int] = ..., property2: _Optional[int] = ..., lastWaterTime: _Optional[str] = ..., leftTime: _Optional[int] = ..., leftPickTime: _Optional[int] = ...) -> None: ...

class TreeUpdateReq(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class TreeUpdateRsp(_message.Message):
    __slots__ = ("tree", "harvestMsg", "pickMsg", "isUpGrade")
    TREE_FIELD_NUMBER: _ClassVar[int]
    HARVESTMSG_FIELD_NUMBER: _ClassVar[int]
    PICKMSG_FIELD_NUMBER: _ClassVar[int]
    ISUPGRADE_FIELD_NUMBER: _ClassVar[int]
    tree: _containers.RepeatedCompositeFieldContainer[TreeInfoMsg]
    harvestMsg: _containers.RepeatedScalarFieldContainer[str]
    pickMsg: _containers.RepeatedScalarFieldContainer[str]
    isUpGrade: bool
    def __init__(self, tree: _Optional[_Iterable[_Union[TreeInfoMsg, _Mapping]]] = ..., harvestMsg: _Optional[_Iterable[str]] = ..., pickMsg: _Optional[_Iterable[str]] = ..., isUpGrade: _Optional[bool] = ...) -> None: ...

class TrialInfoMsg(_message.Message):
    __slots__ = ("index", "skillId", "count", "param1", "param2", "param3", "param4")
    INDEX_FIELD_NUMBER: _ClassVar[int]
    SKILLID_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    PARAM1_FIELD_NUMBER: _ClassVar[int]
    PARAM2_FIELD_NUMBER: _ClassVar[int]
    PARAM3_FIELD_NUMBER: _ClassVar[int]
    PARAM4_FIELD_NUMBER: _ClassVar[int]
    index: int
    skillId: int
    count: int
    param1: int
    param2: int
    param3: int
    param4: int
    def __init__(self, index: _Optional[int] = ..., skillId: _Optional[int] = ..., count: _Optional[int] = ..., param1: _Optional[int] = ..., param2: _Optional[int] = ..., param3: _Optional[int] = ..., param4: _Optional[int] = ...) -> None: ...

class UpdatedSkillMsg(_message.Message):
    __slots__ = ("templateId", "index", "resetResult", "type")
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    INDEX_FIELD_NUMBER: _ClassVar[int]
    RESETRESULT_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    templateId: int
    index: int
    resetResult: bool
    type: int
    def __init__(self, templateId: _Optional[int] = ..., index: _Optional[int] = ..., resetResult: _Optional[bool] = ..., type: _Optional[int] = ...) -> None: ...

class UseConvertCodeMsg(_message.Message):
    __slots__ = ("activeId", "title", "description")
    ACTIVEID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    activeId: str
    title: str
    description: str
    def __init__(self, activeId: _Optional[str] = ..., title: _Optional[str] = ..., description: _Optional[str] = ...) -> None: ...

class UseSkillMsg(_message.Message):
    __slots__ = ("battleId", "heroId", "skillId")
    BATTLEID_FIELD_NUMBER: _ClassVar[int]
    HEROID_FIELD_NUMBER: _ClassVar[int]
    SKILLID_FIELD_NUMBER: _ClassVar[int]
    battleId: str
    heroId: int
    skillId: int
    def __init__(self, battleId: _Optional[str] = ..., heroId: _Optional[int] = ..., skillId: _Optional[int] = ...) -> None: ...

class UserPin(_message.Message):
    __slots__ = ("pin",)
    PIN_FIELD_NUMBER: _ClassVar[int]
    pin: int
    def __init__(self, pin: _Optional[int] = ...) -> None: ...

class UserRebateMsg(_message.Message):
    __slots__ = ("id", "userid", "point", "type", "packagestates")
    ID_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    POINT_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    PACKAGESTATES_FIELD_NUMBER: _ClassVar[int]
    id: str
    userid: int
    point: int
    type: int
    packagestates: _containers.RepeatedCompositeFieldContainer[PackageStateMsg]
    def __init__(self, id: _Optional[str] = ..., userid: _Optional[int] = ..., point: _Optional[int] = ..., type: _Optional[int] = ..., packagestates: _Optional[_Iterable[_Union[PackageStateMsg, _Mapping]]] = ...) -> None: ...

class UserStopMsg(_message.Message):
    __slots__ = ("type", "order")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    ORDER_FIELD_NUMBER: _ClassVar[int]
    type: int
    order: int
    def __init__(self, type: _Optional[int] = ..., order: _Optional[int] = ...) -> None: ...

class VehicleAttackReqMsg(_message.Message):
    __slots__ = ("skillId", "attackType", "suffererNpcId", "suffererId", "effectX", "effectY", "suffererServerName", "suffererNpcIdArray", "attackServerName")
    SKILLID_FIELD_NUMBER: _ClassVar[int]
    ATTACKTYPE_FIELD_NUMBER: _ClassVar[int]
    SUFFERERNPCID_FIELD_NUMBER: _ClassVar[int]
    SUFFERERID_FIELD_NUMBER: _ClassVar[int]
    EFFECTX_FIELD_NUMBER: _ClassVar[int]
    EFFECTY_FIELD_NUMBER: _ClassVar[int]
    SUFFERERSERVERNAME_FIELD_NUMBER: _ClassVar[int]
    SUFFERERNPCIDARRAY_FIELD_NUMBER: _ClassVar[int]
    ATTACKSERVERNAME_FIELD_NUMBER: _ClassVar[int]
    skillId: int
    attackType: int
    suffererNpcId: int
    suffererId: _containers.RepeatedScalarFieldContainer[int]
    effectX: int
    effectY: int
    suffererServerName: _containers.RepeatedScalarFieldContainer[str]
    suffererNpcIdArray: _containers.RepeatedScalarFieldContainer[int]
    attackServerName: str
    def __init__(self, skillId: _Optional[int] = ..., attackType: _Optional[int] = ..., suffererNpcId: _Optional[int] = ..., suffererId: _Optional[_Iterable[int]] = ..., effectX: _Optional[int] = ..., effectY: _Optional[int] = ..., suffererServerName: _Optional[_Iterable[str]] = ..., suffererNpcIdArray: _Optional[_Iterable[int]] = ..., attackServerName: _Optional[str] = ...) -> None: ...

class VehicleAttackRspMsg(_message.Message):
    __slots__ = ("skillId", "npcHurtDataList", "playerHurtDataList", "effectX", "effectY", "attackerId", "serverName", "attackTyep")
    SKILLID_FIELD_NUMBER: _ClassVar[int]
    NPCHURTDATALIST_FIELD_NUMBER: _ClassVar[int]
    PLAYERHURTDATALIST_FIELD_NUMBER: _ClassVar[int]
    EFFECTX_FIELD_NUMBER: _ClassVar[int]
    EFFECTY_FIELD_NUMBER: _ClassVar[int]
    ATTACKERID_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    ATTACKTYEP_FIELD_NUMBER: _ClassVar[int]
    skillId: int
    npcHurtDataList: _containers.RepeatedCompositeFieldContainer[HurtDataMsg]
    playerHurtDataList: _containers.RepeatedCompositeFieldContainer[HurtDataMsg]
    effectX: int
    effectY: int
    attackerId: int
    serverName: str
    attackTyep: int
    def __init__(self, skillId: _Optional[int] = ..., npcHurtDataList: _Optional[_Iterable[_Union[HurtDataMsg, _Mapping]]] = ..., playerHurtDataList: _Optional[_Iterable[_Union[HurtDataMsg, _Mapping]]] = ..., effectX: _Optional[int] = ..., effectY: _Optional[int] = ..., attackerId: _Optional[int] = ..., serverName: _Optional[str] = ..., attackTyep: _Optional[int] = ...) -> None: ...

class VehicleBuffListMsg(_message.Message):
    __slots__ = ("playerBuffStates", "npcBuffStates")
    PLAYERBUFFSTATES_FIELD_NUMBER: _ClassVar[int]
    NPCBUFFSTATES_FIELD_NUMBER: _ClassVar[int]
    playerBuffStates: _containers.RepeatedCompositeFieldContainer[VehicleBuffStateMsg]
    npcBuffStates: _containers.RepeatedCompositeFieldContainer[VehicleBuffStateMsg]
    def __init__(self, playerBuffStates: _Optional[_Iterable[_Union[VehicleBuffStateMsg, _Mapping]]] = ..., npcBuffStates: _Optional[_Iterable[_Union[VehicleBuffStateMsg, _Mapping]]] = ...) -> None: ...

class VehicleBuffStateMsg(_message.Message):
    __slots__ = ("id", "buffId", "state", "playerId", "effectValue", "serverName")
    ID_FIELD_NUMBER: _ClassVar[int]
    BUFFID_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    PLAYERID_FIELD_NUMBER: _ClassVar[int]
    EFFECTVALUE_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    id: int
    buffId: int
    state: int
    playerId: int
    effectValue: int
    serverName: str
    def __init__(self, id: _Optional[int] = ..., buffId: _Optional[int] = ..., state: _Optional[int] = ..., playerId: _Optional[int] = ..., effectValue: _Optional[int] = ..., serverName: _Optional[str] = ...) -> None: ...

class VehicleSkillListMsg(_message.Message):
    __slots__ = ("skillId", "state", "curSum")
    SKILLID_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    CURSUM_FIELD_NUMBER: _ClassVar[int]
    skillId: int
    state: int
    curSum: int
    def __init__(self, skillId: _Optional[int] = ..., state: _Optional[int] = ..., curSum: _Optional[int] = ...) -> None: ...

class VersionMsg(_message.Message):
    __slots__ = ("openVersion", "versionId", "openStory", "module")
    OPENVERSION_FIELD_NUMBER: _ClassVar[int]
    VERSIONID_FIELD_NUMBER: _ClassVar[int]
    OPENSTORY_FIELD_NUMBER: _ClassVar[int]
    MODULE_FIELD_NUMBER: _ClassVar[int]
    openVersion: bool
    versionId: int
    openStory: bool
    module: int
    def __init__(self, openVersion: _Optional[bool] = ..., versionId: _Optional[int] = ..., openStory: _Optional[bool] = ..., module: _Optional[int] = ...) -> None: ...

class VicePasswordMsg(_message.Message):
    __slots__ = ("opType", "inputPass", "prePass", "newPass", "result")
    OPTYPE_FIELD_NUMBER: _ClassVar[int]
    INPUTPASS_FIELD_NUMBER: _ClassVar[int]
    PREPASS_FIELD_NUMBER: _ClassVar[int]
    NEWPASS_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    opType: int
    inputPass: str
    prePass: str
    newPass: str
    result: int
    def __init__(self, opType: _Optional[int] = ..., inputPass: _Optional[str] = ..., prePass: _Optional[str] = ..., newPass: _Optional[str] = ..., result: _Optional[int] = ...) -> None: ...

class VipBoxDropMsg(_message.Message):
    __slots__ = ("weekGiftDate",)
    WEEKGIFTDATE_FIELD_NUMBER: _ClassVar[int]
    weekGiftDate: bytes
    def __init__(self, weekGiftDate: _Optional[bytes] = ...) -> None: ...

class VipInfoMsg(_message.Message):
    __slots__ = ("isVip", "vipGp", "vipGrade", "expirtDate", "isTakeGift", "vipType", "isExpirt", "takeGiftDate")
    ISVIP_FIELD_NUMBER: _ClassVar[int]
    VIPGP_FIELD_NUMBER: _ClassVar[int]
    VIPGRADE_FIELD_NUMBER: _ClassVar[int]
    EXPIRTDATE_FIELD_NUMBER: _ClassVar[int]
    ISTAKEGIFT_FIELD_NUMBER: _ClassVar[int]
    VIPTYPE_FIELD_NUMBER: _ClassVar[int]
    ISEXPIRT_FIELD_NUMBER: _ClassVar[int]
    TAKEGIFTDATE_FIELD_NUMBER: _ClassVar[int]
    isVip: bool
    vipGp: int
    vipGrade: int
    expirtDate: str
    isTakeGift: bool
    vipType: int
    isExpirt: bool
    takeGiftDate: str
    def __init__(self, isVip: _Optional[bool] = ..., vipGp: _Optional[int] = ..., vipGrade: _Optional[int] = ..., expirtDate: _Optional[str] = ..., isTakeGift: _Optional[bool] = ..., vipType: _Optional[int] = ..., isExpirt: _Optional[bool] = ..., takeGiftDate: _Optional[str] = ...) -> None: ...

class VipItemInfoMsg(_message.Message):
    __slots__ = ("tempId", "count")
    TEMPID_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    tempId: int
    count: int
    def __init__(self, tempId: _Optional[int] = ..., count: _Optional[int] = ...) -> None: ...

class VipOpenInfoMsg(_message.Message):
    __slots__ = ("isFriend", "friendId", "friendNickName", "days")
    ISFRIEND_FIELD_NUMBER: _ClassVar[int]
    FRIENDID_FIELD_NUMBER: _ClassVar[int]
    FRIENDNICKNAME_FIELD_NUMBER: _ClassVar[int]
    DAYS_FIELD_NUMBER: _ClassVar[int]
    isFriend: bool
    friendId: int
    friendNickName: str
    days: int
    def __init__(self, isFriend: _Optional[bool] = ..., friendId: _Optional[int] = ..., friendNickName: _Optional[str] = ..., days: _Optional[int] = ...) -> None: ...

class VipRouletteMsg(_message.Message):
    __slots__ = ("leftCount", "needVipItem", "openIndex", "leftItem", "takeItem", "isStart", "opType")
    LEFTCOUNT_FIELD_NUMBER: _ClassVar[int]
    NEEDVIPITEM_FIELD_NUMBER: _ClassVar[int]
    OPENINDEX_FIELD_NUMBER: _ClassVar[int]
    LEFTITEM_FIELD_NUMBER: _ClassVar[int]
    TAKEITEM_FIELD_NUMBER: _ClassVar[int]
    ISSTART_FIELD_NUMBER: _ClassVar[int]
    OPTYPE_FIELD_NUMBER: _ClassVar[int]
    leftCount: int
    needVipItem: int
    openIndex: _containers.RepeatedScalarFieldContainer[int]
    leftItem: _containers.RepeatedCompositeFieldContainer[VipItemInfoMsg]
    takeItem: _containers.RepeatedCompositeFieldContainer[VipItemInfoMsg]
    isStart: bool
    opType: int
    def __init__(self, leftCount: _Optional[int] = ..., needVipItem: _Optional[int] = ..., openIndex: _Optional[_Iterable[int]] = ..., leftItem: _Optional[_Iterable[_Union[VipItemInfoMsg, _Mapping]]] = ..., takeItem: _Optional[_Iterable[_Union[VipItemInfoMsg, _Mapping]]] = ..., isStart: _Optional[bool] = ..., opType: _Optional[int] = ...) -> None: ...

class VipToConsortiaMsg(_message.Message):
    __slots__ = ("userid", "isVip", "vipType", "consortiaId")
    USERID_FIELD_NUMBER: _ClassVar[int]
    ISVIP_FIELD_NUMBER: _ClassVar[int]
    VIPTYPE_FIELD_NUMBER: _ClassVar[int]
    CONSORTIAID_FIELD_NUMBER: _ClassVar[int]
    userid: int
    isVip: bool
    vipType: int
    consortiaId: int
    def __init__(self, userid: _Optional[int] = ..., isVip: _Optional[bool] = ..., vipType: _Optional[int] = ..., consortiaId: _Optional[int] = ...) -> None: ...

class WaitReviveMsg(_message.Message):
    __slots__ = ("battleId", "livingId", "sp", "hp")
    BATTLEID_FIELD_NUMBER: _ClassVar[int]
    LIVINGID_FIELD_NUMBER: _ClassVar[int]
    SP_FIELD_NUMBER: _ClassVar[int]
    HP_FIELD_NUMBER: _ClassVar[int]
    battleId: str
    livingId: int
    sp: int
    hp: int
    def __init__(self, battleId: _Optional[str] = ..., livingId: _Optional[int] = ..., sp: _Optional[int] = ..., hp: _Optional[int] = ...) -> None: ...

class WarFieldAttackMsg(_message.Message):
    __slots__ = ("userId", "serverName", "defenceServerName")
    USERID_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    DEFENCESERVERNAME_FIELD_NUMBER: _ClassVar[int]
    userId: int
    serverName: str
    defenceServerName: str
    def __init__(self, userId: _Optional[int] = ..., serverName: _Optional[str] = ..., defenceServerName: _Optional[str] = ...) -> None: ...

class WarFightInfoMsg(_message.Message):
    __slots__ = ("teamId", "score", "order", "geste", "hitCount", "leftTime", "oneCount", "twoCount", "oneScore", "twoScore")
    TEAMID_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    ORDER_FIELD_NUMBER: _ClassVar[int]
    GESTE_FIELD_NUMBER: _ClassVar[int]
    HITCOUNT_FIELD_NUMBER: _ClassVar[int]
    LEFTTIME_FIELD_NUMBER: _ClassVar[int]
    ONECOUNT_FIELD_NUMBER: _ClassVar[int]
    TWOCOUNT_FIELD_NUMBER: _ClassVar[int]
    ONESCORE_FIELD_NUMBER: _ClassVar[int]
    TWOSCORE_FIELD_NUMBER: _ClassVar[int]
    teamId: int
    score: int
    order: int
    geste: int
    hitCount: int
    leftTime: int
    oneCount: int
    twoCount: int
    oneScore: int
    twoScore: int
    def __init__(self, teamId: _Optional[int] = ..., score: _Optional[int] = ..., order: _Optional[int] = ..., geste: _Optional[int] = ..., hitCount: _Optional[int] = ..., leftTime: _Optional[int] = ..., oneCount: _Optional[int] = ..., twoCount: _Optional[int] = ..., oneScore: _Optional[int] = ..., twoScore: _Optional[int] = ...) -> None: ...

class WarMovieMsg(_message.Message):
    __slots__ = ("score", "geste", "isAdd", "userId", "type", "serverName")
    SCORE_FIELD_NUMBER: _ClassVar[int]
    GESTE_FIELD_NUMBER: _ClassVar[int]
    ISADD_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    score: int
    geste: int
    isAdd: bool
    userId: int
    type: int
    serverName: str
    def __init__(self, score: _Optional[int] = ..., geste: _Optional[int] = ..., isAdd: _Optional[bool] = ..., userId: _Optional[int] = ..., type: _Optional[int] = ..., serverName: _Optional[str] = ...) -> None: ...

class WarReportListMsg(_message.Message):
    __slots__ = ("oneTeamId", "twoTeamId", "thdTemaId", "tempId", "ownCount", "teamCount", "oneScore", "twoScore", "thdScore", "info")
    ONETEAMID_FIELD_NUMBER: _ClassVar[int]
    TWOTEAMID_FIELD_NUMBER: _ClassVar[int]
    THDTEMAID_FIELD_NUMBER: _ClassVar[int]
    TEMPID_FIELD_NUMBER: _ClassVar[int]
    OWNCOUNT_FIELD_NUMBER: _ClassVar[int]
    TEAMCOUNT_FIELD_NUMBER: _ClassVar[int]
    ONESCORE_FIELD_NUMBER: _ClassVar[int]
    TWOSCORE_FIELD_NUMBER: _ClassVar[int]
    THDSCORE_FIELD_NUMBER: _ClassVar[int]
    INFO_FIELD_NUMBER: _ClassVar[int]
    oneTeamId: int
    twoTeamId: int
    thdTemaId: int
    tempId: int
    ownCount: int
    teamCount: int
    oneScore: int
    twoScore: int
    thdScore: int
    info: _containers.RepeatedCompositeFieldContainer[WarReportMsg]
    def __init__(self, oneTeamId: _Optional[int] = ..., twoTeamId: _Optional[int] = ..., thdTemaId: _Optional[int] = ..., tempId: _Optional[int] = ..., ownCount: _Optional[int] = ..., teamCount: _Optional[int] = ..., oneScore: _Optional[int] = ..., twoScore: _Optional[int] = ..., thdScore: _Optional[int] = ..., info: _Optional[_Iterable[_Union[WarReportMsg, _Mapping]]] = ...) -> None: ...

class WarReportMsg(_message.Message):
    __slots__ = ("order", "nickName", "userId", "score", "hitCount", "teamId", "geste", "serverName", "itemCount", "winGesteCount", "seniorStoreCount", "param1", "param2")
    ORDER_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    USERID_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    HITCOUNT_FIELD_NUMBER: _ClassVar[int]
    TEAMID_FIELD_NUMBER: _ClassVar[int]
    GESTE_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    ITEMCOUNT_FIELD_NUMBER: _ClassVar[int]
    WINGESTECOUNT_FIELD_NUMBER: _ClassVar[int]
    SENIORSTORECOUNT_FIELD_NUMBER: _ClassVar[int]
    PARAM1_FIELD_NUMBER: _ClassVar[int]
    PARAM2_FIELD_NUMBER: _ClassVar[int]
    order: int
    nickName: str
    userId: int
    score: int
    hitCount: int
    teamId: int
    geste: int
    serverName: str
    itemCount: int
    winGesteCount: int
    seniorStoreCount: int
    param1: int
    param2: int
    def __init__(self, order: _Optional[int] = ..., nickName: _Optional[str] = ..., userId: _Optional[int] = ..., score: _Optional[int] = ..., hitCount: _Optional[int] = ..., teamId: _Optional[int] = ..., geste: _Optional[int] = ..., serverName: _Optional[str] = ..., itemCount: _Optional[int] = ..., winGesteCount: _Optional[int] = ..., seniorStoreCount: _Optional[int] = ..., param1: _Optional[int] = ..., param2: _Optional[int] = ...) -> None: ...

class WatchInfoMsg(_message.Message):
    __slots__ = ("gridType", "gridPos", "jion1", "jion2", "jion3", "jion4")
    GRIDTYPE_FIELD_NUMBER: _ClassVar[int]
    GRIDPOS_FIELD_NUMBER: _ClassVar[int]
    JION1_FIELD_NUMBER: _ClassVar[int]
    JION2_FIELD_NUMBER: _ClassVar[int]
    JION3_FIELD_NUMBER: _ClassVar[int]
    JION4_FIELD_NUMBER: _ClassVar[int]
    gridType: int
    gridPos: int
    jion1: int
    jion2: int
    jion3: int
    jion4: int
    def __init__(self, gridType: _Optional[int] = ..., gridPos: _Optional[int] = ..., jion1: _Optional[int] = ..., jion2: _Optional[int] = ..., jion3: _Optional[int] = ..., jion4: _Optional[int] = ...) -> None: ...

class WildLandMsg(_message.Message):
    __slots__ = ("id", "mapId", "posX", "posY", "templateId", "type", "occupyPlayerId", "occupyPlayerName", "occupyLeagueName", "level", "refreshTime", "state", "createDate", "simpleHeroInfo", "armyPawn", "curArmyId", "fightCapaity", "bossType", "size")
    ID_FIELD_NUMBER: _ClassVar[int]
    MAPID_FIELD_NUMBER: _ClassVar[int]
    POSX_FIELD_NUMBER: _ClassVar[int]
    POSY_FIELD_NUMBER: _ClassVar[int]
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    OCCUPYPLAYERID_FIELD_NUMBER: _ClassVar[int]
    OCCUPYPLAYERNAME_FIELD_NUMBER: _ClassVar[int]
    OCCUPYLEAGUENAME_FIELD_NUMBER: _ClassVar[int]
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    REFRESHTIME_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    CREATEDATE_FIELD_NUMBER: _ClassVar[int]
    SIMPLEHEROINFO_FIELD_NUMBER: _ClassVar[int]
    ARMYPAWN_FIELD_NUMBER: _ClassVar[int]
    CURARMYID_FIELD_NUMBER: _ClassVar[int]
    FIGHTCAPAITY_FIELD_NUMBER: _ClassVar[int]
    BOSSTYPE_FIELD_NUMBER: _ClassVar[int]
    SIZE_FIELD_NUMBER: _ClassVar[int]
    id: int
    mapId: int
    posX: int
    posY: int
    templateId: int
    type: int
    occupyPlayerId: int
    occupyPlayerName: str
    occupyLeagueName: str
    level: int
    refreshTime: int
    state: int
    createDate: str
    simpleHeroInfo: SimpleHeroInfoMsg
    armyPawn: _containers.RepeatedCompositeFieldContainer[ArmyPawnInfoMsg]
    curArmyId: _containers.RepeatedScalarFieldContainer[int]
    fightCapaity: int
    bossType: int
    size: int
    def __init__(self, id: _Optional[int] = ..., mapId: _Optional[int] = ..., posX: _Optional[int] = ..., posY: _Optional[int] = ..., templateId: _Optional[int] = ..., type: _Optional[int] = ..., occupyPlayerId: _Optional[int] = ..., occupyPlayerName: _Optional[str] = ..., occupyLeagueName: _Optional[str] = ..., level: _Optional[int] = ..., refreshTime: _Optional[int] = ..., state: _Optional[int] = ..., createDate: _Optional[str] = ..., simpleHeroInfo: _Optional[_Union[SimpleHeroInfoMsg, _Mapping]] = ..., armyPawn: _Optional[_Iterable[_Union[ArmyPawnInfoMsg, _Mapping]]] = ..., curArmyId: _Optional[_Iterable[int]] = ..., fightCapaity: _Optional[int] = ..., bossType: _Optional[int] = ..., size: _Optional[int] = ...) -> None: ...

class WildYieldMsg(_message.Message):
    __slots__ = ("wildPoxName", "wildPox", "wildGrade", "wildName", "wildYield", "wildRefreshTime", "mapId", "createTime")
    WILDPOXNAME_FIELD_NUMBER: _ClassVar[int]
    WILDPOX_FIELD_NUMBER: _ClassVar[int]
    WILDGRADE_FIELD_NUMBER: _ClassVar[int]
    WILDNAME_FIELD_NUMBER: _ClassVar[int]
    WILDYIELD_FIELD_NUMBER: _ClassVar[int]
    WILDREFRESHTIME_FIELD_NUMBER: _ClassVar[int]
    MAPID_FIELD_NUMBER: _ClassVar[int]
    CREATETIME_FIELD_NUMBER: _ClassVar[int]
    wildPoxName: str
    wildPox: str
    wildGrade: int
    wildName: str
    wildYield: int
    wildRefreshTime: int
    mapId: int
    createTime: str
    def __init__(self, wildPoxName: _Optional[str] = ..., wildPox: _Optional[str] = ..., wildGrade: _Optional[int] = ..., wildName: _Optional[str] = ..., wildYield: _Optional[int] = ..., wildRefreshTime: _Optional[int] = ..., mapId: _Optional[int] = ..., createTime: _Optional[str] = ...) -> None: ...

class WinConditionsMsg(_message.Message):
    __slots__ = ("conditionsByte",)
    CONDITIONSBYTE_FIELD_NUMBER: _ClassVar[int]
    conditionsByte: int
    def __init__(self, conditionsByte: _Optional[int] = ...) -> None: ...

class WorldBossBufferMsg(_message.Message):
    __slots__ = ("type", "pointValue", "giftValue", "op", "result", "wound")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    POINTVALUE_FIELD_NUMBER: _ClassVar[int]
    GIFTVALUE_FIELD_NUMBER: _ClassVar[int]
    OP_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    WOUND_FIELD_NUMBER: _ClassVar[int]
    type: int
    pointValue: int
    giftValue: int
    op: int
    result: int
    wound: int
    def __init__(self, type: _Optional[int] = ..., pointValue: _Optional[int] = ..., giftValue: _Optional[int] = ..., op: _Optional[int] = ..., result: _Optional[int] = ..., wound: _Optional[int] = ...) -> None: ...

class WorldBossInfoLoadMsg(_message.Message):
    __slots__ = ("campaignId", "leftTime")
    CAMPAIGNID_FIELD_NUMBER: _ClassVar[int]
    LEFTTIME_FIELD_NUMBER: _ClassVar[int]
    campaignId: int
    leftTime: int
    def __init__(self, campaignId: _Optional[int] = ..., leftTime: _Optional[int] = ...) -> None: ...

class WorldBossInfoMsg(_message.Message):
    __slots__ = ("curHp", "totalNum", "campaignId", "woundInfo", "totalHp", "myWound", "grades", "currentMillis", "castleWound", "bufferGrade")
    CURHP_FIELD_NUMBER: _ClassVar[int]
    TOTALNUM_FIELD_NUMBER: _ClassVar[int]
    CAMPAIGNID_FIELD_NUMBER: _ClassVar[int]
    WOUNDINFO_FIELD_NUMBER: _ClassVar[int]
    TOTALHP_FIELD_NUMBER: _ClassVar[int]
    MYWOUND_FIELD_NUMBER: _ClassVar[int]
    GRADES_FIELD_NUMBER: _ClassVar[int]
    CURRENTMILLIS_FIELD_NUMBER: _ClassVar[int]
    CASTLEWOUND_FIELD_NUMBER: _ClassVar[int]
    BUFFERGRADE_FIELD_NUMBER: _ClassVar[int]
    curHp: int
    totalNum: int
    campaignId: int
    woundInfo: _containers.RepeatedCompositeFieldContainer[WoundInfoMsg]
    totalHp: int
    myWound: int
    grades: int
    currentMillis: int
    castleWound: _containers.RepeatedCompositeFieldContainer[WoundInfoMsg]
    bufferGrade: int
    def __init__(self, curHp: _Optional[int] = ..., totalNum: _Optional[int] = ..., campaignId: _Optional[int] = ..., woundInfo: _Optional[_Iterable[_Union[WoundInfoMsg, _Mapping]]] = ..., totalHp: _Optional[int] = ..., myWound: _Optional[int] = ..., grades: _Optional[int] = ..., currentMillis: _Optional[int] = ..., castleWound: _Optional[_Iterable[_Union[WoundInfoMsg, _Mapping]]] = ..., bufferGrade: _Optional[int] = ...) -> None: ...

class WorldBossInfoStateMsg(_message.Message):
    __slots__ = ("campaignId", "state")
    CAMPAIGNID_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    campaignId: int
    state: int
    def __init__(self, campaignId: _Optional[int] = ..., state: _Optional[int] = ...) -> None: ...

class WorldBossLiveMsg(_message.Message):
    __slots__ = ("op",)
    OP_FIELD_NUMBER: _ClassVar[int]
    op: int
    def __init__(self, op: _Optional[int] = ...) -> None: ...

class WorldBossMsg(_message.Message):
    __slots__ = ("armyId", "mapId", "param1", "param2", "param3", "param4")
    ARMYID_FIELD_NUMBER: _ClassVar[int]
    MAPID_FIELD_NUMBER: _ClassVar[int]
    PARAM1_FIELD_NUMBER: _ClassVar[int]
    PARAM2_FIELD_NUMBER: _ClassVar[int]
    PARAM3_FIELD_NUMBER: _ClassVar[int]
    PARAM4_FIELD_NUMBER: _ClassVar[int]
    armyId: int
    mapId: int
    param1: int
    param2: int
    param3: str
    param4: str
    def __init__(self, armyId: _Optional[int] = ..., mapId: _Optional[int] = ..., param1: _Optional[int] = ..., param2: _Optional[int] = ..., param3: _Optional[str] = ..., param4: _Optional[str] = ...) -> None: ...

class WorldBossPlayerStateMsg(_message.Message):
    __slots__ = ("armyId", "state", "leftTime", "serverName", "resCount", "npcNodeId", "templateId", "isNewBorn", "posX", "posY")
    ARMYID_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    LEFTTIME_FIELD_NUMBER: _ClassVar[int]
    SERVERNAME_FIELD_NUMBER: _ClassVar[int]
    RESCOUNT_FIELD_NUMBER: _ClassVar[int]
    NPCNODEID_FIELD_NUMBER: _ClassVar[int]
    TEMPLATEID_FIELD_NUMBER: _ClassVar[int]
    ISNEWBORN_FIELD_NUMBER: _ClassVar[int]
    POSX_FIELD_NUMBER: _ClassVar[int]
    POSY_FIELD_NUMBER: _ClassVar[int]
    armyId: int
    state: int
    leftTime: int
    serverName: str
    resCount: int
    npcNodeId: int
    templateId: int
    isNewBorn: int
    posX: int
    posY: int
    def __init__(self, armyId: _Optional[int] = ..., state: _Optional[int] = ..., leftTime: _Optional[int] = ..., serverName: _Optional[str] = ..., resCount: _Optional[int] = ..., npcNodeId: _Optional[int] = ..., templateId: _Optional[int] = ..., isNewBorn: _Optional[int] = ..., posX: _Optional[int] = ..., posY: _Optional[int] = ...) -> None: ...

class WorldBossReportMsg(_message.Message):
    __slots__ = ("campaignId", "order", "gold", "strengy", "totalWound", "type")
    CAMPAIGNID_FIELD_NUMBER: _ClassVar[int]
    ORDER_FIELD_NUMBER: _ClassVar[int]
    GOLD_FIELD_NUMBER: _ClassVar[int]
    STRENGY_FIELD_NUMBER: _ClassVar[int]
    TOTALWOUND_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    campaignId: int
    order: int
    gold: int
    strengy: int
    totalWound: int
    type: int
    def __init__(self, campaignId: _Optional[int] = ..., order: _Optional[int] = ..., gold: _Optional[int] = ..., strengy: _Optional[int] = ..., totalWound: _Optional[int] = ..., type: _Optional[int] = ...) -> None: ...

class WorldBossStateMsg(_message.Message):
    __slots__ = ("worldBossInfo",)
    WORLDBOSSINFO_FIELD_NUMBER: _ClassVar[int]
    worldBossInfo: _containers.RepeatedCompositeFieldContainer[WorldBossInfoStateMsg]
    def __init__(self, worldBossInfo: _Optional[_Iterable[_Union[WorldBossInfoStateMsg, _Mapping]]] = ...) -> None: ...

class WorldBossWoundRewardListMsg(_message.Message):
    __slots__ = ("rewardinfo",)
    REWARDINFO_FIELD_NUMBER: _ClassVar[int]
    rewardinfo: _containers.RepeatedCompositeFieldContainer[WorldBossWoundRewardMsg]
    def __init__(self, rewardinfo: _Optional[_Iterable[_Union[WorldBossWoundRewardMsg, _Mapping]]] = ...) -> None: ...

class WorldBossWoundRewardMsg(_message.Message):
    __slots__ = ("campaignId", "rewardid", "woundmsg", "rewardmsg", "state")
    CAMPAIGNID_FIELD_NUMBER: _ClassVar[int]
    REWARDID_FIELD_NUMBER: _ClassVar[int]
    WOUNDMSG_FIELD_NUMBER: _ClassVar[int]
    REWARDMSG_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    campaignId: int
    rewardid: int
    woundmsg: str
    rewardmsg: str
    state: int
    def __init__(self, campaignId: _Optional[int] = ..., rewardid: _Optional[int] = ..., woundmsg: _Optional[str] = ..., rewardmsg: _Optional[str] = ..., state: _Optional[int] = ...) -> None: ...

class WoundInfoMsg(_message.Message):
    __slots__ = ("userId", "nickName", "wound", "woundAddation", "job")
    USERID_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    WOUND_FIELD_NUMBER: _ClassVar[int]
    WOUNDADDATION_FIELD_NUMBER: _ClassVar[int]
    JOB_FIELD_NUMBER: _ClassVar[int]
    userId: int
    nickName: str
    wound: int
    woundAddation: int
    job: int
    def __init__(self, userId: _Optional[int] = ..., nickName: _Optional[str] = ..., wound: _Optional[int] = ..., woundAddation: _Optional[int] = ..., job: _Optional[int] = ...) -> None: ...

class answerquestionorderMsg(_message.Message):
    __slots__ = ("userId", "nickName", "curOrder", "currentScore")
    USERID_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    CURORDER_FIELD_NUMBER: _ClassVar[int]
    CURRENTSCORE_FIELD_NUMBER: _ClassVar[int]
    userId: int
    nickName: str
    curOrder: int
    currentScore: int
    def __init__(self, userId: _Optional[int] = ..., nickName: _Optional[str] = ..., curOrder: _Optional[int] = ..., currentScore: _Optional[int] = ...) -> None: ...

class playeranswerquestionMsg(_message.Message):
    __slots__ = ("userId", "curOrder", "currentScore", "getEXP", "playerAnswerSucCount", "doubleBlessCount", "wisdomHeartCount", "choiceEyesCount", "extraEXP", "goDate")
    USERID_FIELD_NUMBER: _ClassVar[int]
    CURORDER_FIELD_NUMBER: _ClassVar[int]
    CURRENTSCORE_FIELD_NUMBER: _ClassVar[int]
    GETEXP_FIELD_NUMBER: _ClassVar[int]
    PLAYERANSWERSUCCOUNT_FIELD_NUMBER: _ClassVar[int]
    DOUBLEBLESSCOUNT_FIELD_NUMBER: _ClassVar[int]
    WISDOMHEARTCOUNT_FIELD_NUMBER: _ClassVar[int]
    CHOICEEYESCOUNT_FIELD_NUMBER: _ClassVar[int]
    EXTRAEXP_FIELD_NUMBER: _ClassVar[int]
    GODATE_FIELD_NUMBER: _ClassVar[int]
    userId: int
    curOrder: int
    currentScore: int
    getEXP: int
    playerAnswerSucCount: int
    doubleBlessCount: int
    wisdomHeartCount: int
    choiceEyesCount: int
    extraEXP: int
    goDate: str
    def __init__(self, userId: _Optional[int] = ..., curOrder: _Optional[int] = ..., currentScore: _Optional[int] = ..., getEXP: _Optional[int] = ..., playerAnswerSucCount: _Optional[int] = ..., doubleBlessCount: _Optional[int] = ..., wisdomHeartCount: _Optional[int] = ..., choiceEyesCount: _Optional[int] = ..., extraEXP: _Optional[int] = ..., goDate: _Optional[str] = ...) -> None: ...

class singleranswerquestionMsg(_message.Message):
    __slots__ = ("id", "question", "option1", "option2", "option3", "option4", "answer")
    ID_FIELD_NUMBER: _ClassVar[int]
    QUESTION_FIELD_NUMBER: _ClassVar[int]
    OPTION1_FIELD_NUMBER: _ClassVar[int]
    OPTION2_FIELD_NUMBER: _ClassVar[int]
    OPTION3_FIELD_NUMBER: _ClassVar[int]
    OPTION4_FIELD_NUMBER: _ClassVar[int]
    ANSWER_FIELD_NUMBER: _ClassVar[int]
    id: int
    question: str
    option1: str
    option2: str
    option3: str
    option4: str
    answer: int
    def __init__(self, id: _Optional[int] = ..., question: _Optional[str] = ..., option1: _Optional[str] = ..., option2: _Optional[str] = ..., option3: _Optional[str] = ..., option4: _Optional[str] = ..., answer: _Optional[int] = ...) -> None: ...
