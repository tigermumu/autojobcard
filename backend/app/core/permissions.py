from typing import Dict, List


class PermissionCodes:
    MODULE_ENGLISH = "module:english"
    MODULE_CHINESE = "module:chinese"
    MODULE_DEFECT_CHECK = "module:defect_check"
    MODULE_ADMIN = "module:admin"

    ENGLISH_MAIN = "page:english.main"

    CHINESE_MAIN = "page:chinese.main"
    CHINESE_SCHEME = "page:chinese.scheme"
    CHINESE_KEYWORDS = "page:chinese.keywords"

    DEFECT_CHECK_SINGLE = "page:defect_check.single"
    DEFECT_CHECK_SEAT = "page:defect_check.seat"
    DEFECT_CHECK_CREW_SEAT = "page:defect_check.crew_seat"
    DEFECT_CHECK_BATCH = "page:defect_check.batch"
    DEFECT_CHECK_EXPORT = "page:defect_check.export"
    DEFECT_CHECK_CATALOG = "page:defect_check.catalog"
    DEFECT_CHECK_CUSTOM = "page:defect_check.custom"

    ADMIN_USER_MANAGEMENT = "page:admin.user_management"


PERMISSION_GROUPS: Dict[str, List[str]] = {
    "英文工卡批量导入": [
        PermissionCodes.MODULE_ENGLISH,
        PermissionCodes.ENGLISH_MAIN,
    ],
    "中文工卡批量处理": [
        PermissionCodes.MODULE_CHINESE,
        PermissionCodes.CHINESE_MAIN,
        PermissionCodes.CHINESE_SCHEME,
        PermissionCodes.CHINESE_KEYWORDS,
    ],
    "缺陷检查": [
        PermissionCodes.MODULE_DEFECT_CHECK,
        PermissionCodes.DEFECT_CHECK_SINGLE,
        PermissionCodes.DEFECT_CHECK_SEAT,
        PermissionCodes.DEFECT_CHECK_CREW_SEAT,
        PermissionCodes.DEFECT_CHECK_BATCH,
        PermissionCodes.DEFECT_CHECK_EXPORT,
        PermissionCodes.DEFECT_CHECK_CATALOG,
        PermissionCodes.DEFECT_CHECK_CUSTOM,
    ],
    "后台管理": [
        PermissionCodes.MODULE_ADMIN,
        PermissionCodes.ADMIN_USER_MANAGEMENT,
    ],
}


ALL_PERMISSIONS: List[str] = [
    permission
    for permissions in PERMISSION_GROUPS.values()
    for permission in permissions
]
