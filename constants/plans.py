import enum


class PLAN_TYPE(enum.Enum):
    FREE = 0
    CREDIT_BASED = 1
    SUBSCRIPTION_BASED = 2


class SUBSCRIPTION_TIER(enum.Enum):
    FREE = 0
    BASIC = 1
    PRO = 2


class CREDIT_BASED_PLANS_BASIC(enum.Enum):
    FREE = 15
    STARTER = 100
    GROWTH = 250
    EXPANSION = 500
    ENTERPRISE = 2000


class CREDIT_BASED_PLANS_PRO(enum.Enum):
    STARTER = 100
    GROWTH = 250
    EXPANSION = 500
    ENTERPRISE = 2000


class SUB_BASED_PLANS_BASIC(enum.Enum):
    BASIC_ESSENTIALS = 80 * 3
    BASIC_PRO = 200 * 3
    BASIC_ELITE = 600 * 6
    BASIC_UNLIMITED = 2000 * 6


class SUB_BASED_PLANS_PRO(enum.Enum):
    PRO_ESSENTIALS = 80 * 3
    PRO_PLUS = 200 * 3
    PRO_ELITE = 600 * 6
    PRO_UNLIMITED = 2000 * 6


class Duration(enum.Enum):
    NONE = 0
    THREE_MONTHS = 1
    SIX_MONTHS = 2
