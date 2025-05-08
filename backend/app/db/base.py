"""鏁版嵁搴撴ā鍨嬪熀绫诲畾涔?

璇ユ枃浠跺鍏ユ墍鏈夌殑鏁版嵁搴撴ā鍨嬶紝浣垮緱Alembic鍙互鑷姩鍙戠幇妯″瀷鍙樻洿銆?
鍦ㄦ坊鍔犳柊妯″瀷鍚庯紝蹇呴』鍦ㄦ澶勫鍏ュ畠浠紝浠ヤ究杩佺Щ宸ュ叿鑳藉妫€娴嬪埌鍙樺寲銆?
"""

from app.db.session import Base

# 瀵煎叆鎵€鏈夋ā鍨嬶紝浣緼lembic鑳藉妫€娴嬪埌瀹冧滑
from app.db.models import (
    User,
    Role,
    UserRole,
    SystemConfig,
    OperationLog,
    KnowledgeBase,
    KnowledgeEntry,
    Product,
    Order,
    OrderItem,
    AIQueryLog,
)

# 渚嬪锛?
# from app.models.user import User
# from app.models.item import Item 
