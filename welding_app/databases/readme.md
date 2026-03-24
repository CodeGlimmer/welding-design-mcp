# 数据库结构

## welding_scenario

### tables
- local_file
  - id
  - welding_scenario_id
  - file_position

- welding_scenarios
  - id
  - welding_scenario_id: 如果在local_file中存在，则与之一致，否则额外生成
  - object: 焊接方案对象的存储，依赖pickle
