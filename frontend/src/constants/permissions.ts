export const PermissionCodes = {
  MODULE_ENGLISH: 'module:english',
  MODULE_CHINESE: 'module:chinese',
  MODULE_DEFECT_CHECK: 'module:defect_check',
  MODULE_ADMIN: 'module:admin',

  ENGLISH_MAIN: 'page:english.main',

  CHINESE_MAIN: 'page:chinese.main',
  CHINESE_SCHEME: 'page:chinese.scheme',
  CHINESE_KEYWORDS: 'page:chinese.keywords',

  DEFECT_CHECK_SINGLE: 'page:defect_check.single',
  DEFECT_CHECK_SEAT: 'page:defect_check.seat',
  DEFECT_CHECK_CREW_SEAT: 'page:defect_check.crew_seat',
  DEFECT_CHECK_BATCH: 'page:defect_check.batch',
  DEFECT_CHECK_EXPORT: 'page:defect_check.export',
  DEFECT_CHECK_CATALOG: 'page:defect_check.catalog',
  DEFECT_CHECK_CUSTOM: 'page:defect_check.custom',

  ADMIN_USER_MANAGEMENT: 'page:admin.user_management',
} as const

export type PermissionCode = typeof PermissionCodes[keyof typeof PermissionCodes]

export const permissionGroups: Array<{ title: string; items: Array<{ code: PermissionCode; label: string }> }> = [
  {
    title: '英文工卡批量导入',
    items: [
      { code: PermissionCodes.MODULE_ENGLISH, label: '模块访问' },
      { code: PermissionCodes.ENGLISH_MAIN, label: '英文工卡批量导入页' },
    ],
  },
  {
    title: '中文工卡批量处理',
    items: [
      { code: PermissionCodes.MODULE_CHINESE, label: '模块访问' },
      { code: PermissionCodes.CHINESE_MAIN, label: '中文工卡批量处理页' },
      { code: PermissionCodes.CHINESE_SCHEME, label: '标准缺陷方案功能' },
      { code: PermissionCodes.CHINESE_KEYWORDS, label: '关键词管理功能' },
    ],
  },
  {
    title: '缺陷检查',
    items: [
      { code: PermissionCodes.MODULE_DEFECT_CHECK, label: '模块访问' },
      { code: PermissionCodes.DEFECT_CHECK_SINGLE, label: '厨卫部件检查' },
      { code: PermissionCodes.DEFECT_CHECK_SEAT, label: '旅客座椅缺陷检查' },
      { code: PermissionCodes.DEFECT_CHECK_CREW_SEAT, label: '机组座椅缺陷检查' },
      { code: PermissionCodes.DEFECT_CHECK_BATCH, label: '天行侧部件检查' },
      { code: PermissionCodes.DEFECT_CHECK_EXPORT, label: '缺陷清单导出' },
      { code: PermissionCodes.DEFECT_CHECK_CATALOG, label: '标准缺陷描述数据表' },
      { code: PermissionCodes.DEFECT_CHECK_CUSTOM, label: '自定义缺陷描述' },
    ],
  },
  {
    title: '后台管理',
    items: [
      { code: PermissionCodes.MODULE_ADMIN, label: '模块访问' },
      { code: PermissionCodes.ADMIN_USER_MANAGEMENT, label: '会员与权限管理' },
    ],
  },
]
