# CS1302A 复习排程器 v1

只需 Python 3.9 或以上，无需安装依赖。从**仓库根目录**运行：

```sh
cd /Users/justin/Documents/1302A-projecct-spare
python3 -m study_plan --demo
python3 -m study_plan
```

一分钟演示：运行第一条 Python 命令，打开输出路径的 `study_plan.html`（可在文件管理器双击，或把输出的 `file://` 地址粘贴到浏览器）。两科固定数据从 2026-11-09 开始，每天 19:00–20:00。CS1302A 在 11 月 11 日考试，需要 180 分钟，但考前只有 120 分钟，因此缺 60 分钟；数学需要的 180 分钟全部排入。重复运行会覆盖当前目录的 HTML。

交互模式按提示输入开始日期、每天的空闲时段数量及起止时间、科目数量，以及各科名称、考试日期和剩余分钟数。时间使用 24 小时制，起止均在 :00 或 :30；24:00 只可用作结束。可输入多个不重叠的时段，连续 7 天使用相同设置。时长必须为正整数且是 30 的整数倍。考试已到或在计划开始前的科目会全部列为未排完。

## 模块及数据

- `input_ui.py`：校验并返回 `(start_date, tasks, slots)`。日期用 `datetime.date`；时间用午夜起的分钟数。任务字典为 `{subject, exam_date, minutes}`，空闲时段字典为 `{date, start, end}`。
- `scheduler.py`：`schedule(tasks, slots)` 返回 `(sessions, unscheduled)`，不读写终端或文件，不修改输入。按考试日期升序，同日考试保留输入顺序，为每科依次使用最早可用的半小时格；考试当天及之后不安排，重叠输入的空闲格也只使用一次。安排字典为 `{date, start, end, subject, subject_id}`，未排入字典为 `{subject, remaining_minutes}`。
- `calendar_view.py`：`save_calendar(start_date, slots, sessions, unscheduled)` 生成横向日期、纵向时间的 HTML 并返回绝对路径，科目文字经过 HTML 转义。
- `__main__.py`：取得交互或固定演示数据，调用同一个排程函数和 HTML 函数。

每条安排为 30 分钟，连续安排显示为相邻格子。缺口列在日历下方。第一版不包含休息偏好或跨周补排。

运行标准库验证：

```sh
python3 -m unittest discover -s tests -v
```

原有 `work folder/` 与 `draft folder/` 保留；新包放在根目录，避免影响组员占位文件。生成的 HTML、缓存、虚拟环境和本地草稿不纳入新提交。
