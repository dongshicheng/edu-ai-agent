SLIDE_GENERATION_PROMPT = """你是一位资深教学课件设计师。根据以下教学意图和参考资料，生成PPT课件的逐页规格。

教学意图：
{intent}

参考资料：
{context}

请生成一个JSON数组，每个元素代表一页PPT，格式如下：
{{
  "slides": [
    {{
      "slide_number": 1,
      "layout": "cover",
      "title": "课题名称",
      "subtitle": "副标题（学科/年级）",
      "bullets": [],
      "notes": "教师备注"
    }},
    {{
      "slide_number": 2,
      "layout": "toc",
      "title": "目录",
      "bullets": ["一、xxx", "二、xxx"],
      "notes": ""
    }},
    {{
      "slide_number": 3,
      "layout": "content",
      "title": "页面标题",
      "bullets": ["要点1", "要点2", "要点3"],
      "notes": "详细讲解说明..."
    }}
  ]
}}

布局类型(layout)：
- "cover": 封面页
- "toc": 目录页
- "content": 正文内容页（标题+要点列表）
- "two_column": 双栏对比页
- "summary": 总结页
- "exercise": 练习/互动页

要求：
1. 总页数 10-20 页
2. 结构：封面 → 目录 → 导入(1-2页) → 正文(6-12页) → 总结(1页) → 练习(1-2页)
3. 每页要点控制在 3-5 条
4. 每条要点 15-30 字，简洁有力
5. notes 字段写入详细的教师讲解提示
6. 内容紧扣教学目标和重难点"""

DOC_GENERATION_PROMPT = """你是一位资深教学设计师。根据以下教学意图和参考资料，生成一份完整的教案。

教学意图：
{intent}

参考资料：
{context}

请以JSON格式输出教案，格式如下：
{{
  "title": "课题名称",
  "subject": "学科",
  "grade_level": "年级",
  "duration": "课时",
  "objectives": [
    "知识目标：xxx",
    "能力目标：xxx",
    "情感目标：xxx"
  ],
  "key_points": ["教学重点1", "教学重点2"],
  "difficulty_points": ["教学难点1"],
  "teaching_aids": ["教具和准备"],
  "teaching_process": [
    {{
      "stage": "导入新课",
      "duration": "5分钟",
      "teacher_activity": "教师活动描述...",
      "student_activity": "学生活动描述...",
      "design_intent": "设计意图说明..."
    }},
    {{
      "stage": "新知讲授",
      "duration": "20分钟",
      "teacher_activity": "...",
      "student_activity": "...",
      "design_intent": "..."
    }}
  ],
  "homework": ["作业1", "作业2"],
  "board_design": "板书设计描述",
  "reflection": "教学反思（预留）"
}}

要求：
1. 教学过程分为 4-6 个阶段
2. 每个阶段包含教师活动、学生活动、设计意图
3. 内容详实，可直接用于教学
4. 紧扣教学目标和重难点"""
