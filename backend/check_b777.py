"""快速查询B-777索引数据条数 - 使用API统计接口"""
# 这个脚本需要后端服务运行
# 或者可以直接在前端页面查看统计信息

print("""
要查询B-777构型的索引数据条数，有以下几种方法：

1. 通过前端页面查看：
   - 访问 http://localhost:3000/configurations
   - 选择B-777构型
   - 查看统计信息卡片中的"二级子部件"数量（这代表索引数据条数）

2. 通过API查询（需要后端服务运行）：
   - GET http://localhost:8000/api/v1/index-data/configuration/{configuration_id}/statistics
   - 先查询构型ID，然后查询统计信息

3. 使用Python脚本查询（需要Python环境）：
   - 运行: python query_b777_count.py
""")


