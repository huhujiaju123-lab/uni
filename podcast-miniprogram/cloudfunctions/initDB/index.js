/**
 * initDB 云函数 — 初始化数据库 + 灌入测试数据
 * 在开发者工具「云开发控制台 → 云函数 → initDB → 测试」中调用
 */
const cloud = require('wx-server-sdk')
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })
const db = cloud.database()

// 测试数据：EP.59 一生之敌（精简版，验证渲染链路）
const TEST_EPISODE = {
  episode_id: '674a16478d5d7e073a18b4cc',
  meta: {
    podcast_name: '自习室 STUDYROOM',
    episode_number: 59,
    title: '一生之敌｜没有天赋、不谈热爱，凡人的突围只有与自我的持久厮杀',
    subtitle: '《The War of Art》（一生之敌）',
    total_duration_sec: 5344,
    language: 'zh',
    cover_url: 'https://image.xyzcdn.net/FlVp6xDa8RCnaBfh68xENgTHBNP0.jpg',
    platform_links: { xiaoyuzhou: 'https://www.xiaoyuzhoufm.com/episode/674a16478d5d7e073a18b4cc' }
  },
  participants: [
    { id: 'host-weiya', name: '维亚', role: 'host', bio: '主持人' },
    { id: 'host-guxin', name: '股心', role: 'host', bio: '主持人（写作者）' }
  ],
  featured_work: {
    type: 'book',
    title: '《The War of Art》（一生之敌）',
    author: 'Steven Pressfield'
  },
  sections: [
    {
      id: 'intro',
      title: '开场：两个人生之间的那道墙',
      subtitle: '书籍介绍与作者生平',
      start_sec: 0,
      end_sec: 488,
      is_ad: false,
      key_points: [
        '《一生之敌》：一本言简意赅、只讲一件事的书——内阻力（Resistance）',
        '真正的作家知道的秘密：写作不是写作，而是坐下来开始写',
        '阻止我们坐下来的，就叫内阻力'
      ],
      key_points_grouped: [
        {
          label: '核心概念',
          visual_type: 'list',
          points: [
            { text: '内阻力是阻止我们坐下来开始做事的力量', detail: '书中用 Resistance 这个词来描述' },
            { text: '写作的秘密不是灵感，是坐下来开始写', detail: '所有专业作家都知道这一点' }
          ]
        }
      ],
      quotes: ['我们的人生有两个版本：一个是我们正在过的，另一个是没有活出来的。'],
      stories: [],
      section_context: '介绍了这本书讲的是什么——内阻力，以及作者的传奇人生'
    },
    {
      id: 'resistance-nature',
      title: '内阻力的本质：它是一种反人类力量',
      subtitle: '为什么越重要的事越难开始',
      start_sec: 488,
      end_sec: 1500,
      is_ad: false,
      key_points: [
        '内阻力是一种反人类力量，专门对付创造性工作',
        '越重要的事情，内阻力越大',
        '内阻力的特征：无形、无个人属性、不可协商'
      ],
      key_points_grouped: [
        {
          label: '内阻力的特征',
          visual_type: 'icon-grid',
          points: [
            { text: '内阻力是一种反人类力量', detail: '它不会在你做琐事时出现，专门对付重要的创造性工作' },
            { text: '越重要的事情，内阻力越大', detail: '写小说比刷手机难开始，因为写小说对你更重要' },
            { text: '它无形、无个人属性、不可协商', detail: '你不能跟它讲道理，只能硬刚' }
          ]
        }
      ],
      diagram: {
        type: 'flow',
        title: '内阻力的升级路径',
        steps: [
          { label: '产生想法', desc: '有了一个重要的创造性目标' },
          { label: '内阻力出现', desc: '拖延、恐惧、自我怀疑' },
          { label: '两个选择', desc: '屈服（放弃）或抵抗（开始工作）' },
          { label: '持续抵抗', desc: '每天坐下来，变成职业选手' }
        ]
      },
      quotes: ['内阻力越大，说明这件事对你的灵魂越重要。'],
      stories: [{ narrator_id: 'host-guxin', text: '股心分享了自己写作时的拖延经历：每次打开电脑准备写，总会先去泡茶、整理桌面、刷一下手机。' }],
      section_context: '聊了内阻力到底是啥——一种专门对付你做重要事情的力量'
    },
    {
      id: 'overcome',
      title: '克服内阻力：成为职业选手',
      subtitle: '业余与职业的区别',
      start_sec: 1500,
      end_sec: 3000,
      is_ad: false,
      key_points: [
        '业余选手等灵感，职业选手每天坐下来工作',
        '职业选手知道恐惧不会消失，但选择穿过恐惧',
        '把创作当成上班：定时定点，不管状态好不好'
      ],
      key_points_grouped: [
        {
          label: '业余 vs 职业',
          visual_type: 'comparison',
          points: [
            { text: '业余选手等灵感来了才开始', detail: '把创作当兴趣，好的时候做，不好的时候不做' },
            { text: '职业选手不管有没有灵感都坐下来工作', detail: '像上班一样，定时定点，这才是真正的创作者' }
          ]
        }
      ],
      diagram: {
        type: 'comparison',
        title: '业余选手 vs 职业选手',
        left: { label: '业余选手' },
        right: { label: '职业选手' },
        entries: [
          { left: '等灵感', right: '每天坐下来' },
          { left: '怕失败就不开始', right: '怕失败但还是开始' },
          { left: '把创作当兴趣', right: '把创作当工作' },
          { left: '被内阻力打败', right: '穿过内阻力' }
        ]
      },
      quotes: ['职业选手不是不怕，是怕了也去做。'],
      stories: [],
      section_context: '核心观点——想克服拖延就要从业余选手变成职业选手，每天坐下来干活'
    }
  ],
  core_quotes: [
    '我们的人生有两个版本：一个是我们正在过的，另一个是没有活出来的。',
    '内阻力越大，说明这件事对你的灵魂越重要。',
    '职业选手不是不怕，是怕了也去做。',
    '写作不是写作，而是坐下来开始写。',
    '你唯一需要战胜的敌人，就是你自己。'
  ],
  content_overview: {
    one_sentence_summary: '拖延和自我怀疑的真正原因是内阻力，克服它的唯一方法是像职业选手一样每天坐下来工作。',
    content_blocks: [
      { id: 'block-1', title: '什么是内阻力', summary: '一种阻止你做重要事情的力量', section_ids: ['intro', 'resistance-nature'], icon: '🧱' },
      { id: 'block-2', title: '如何克服', summary: '成为职业选手，每天坐下来', section_ids: ['overcome'], icon: '💪' }
    ],
    block_connections: [
      { from: 'block-1', to: 'block-2', relation: '递进', description: '认识了内阻力之后，讲怎么打败它' }
    ]
  },
  arguments: [
    { id: 'arg-1', claim: '内阻力是所有创造性工作的最大敌人', evidence_type: '逻辑推演', evidence: '作者用数十年创作经验总结', source_section_id: 'resistance-nature', strength: 'strong' },
    { id: 'arg-2', claim: '克服拖延的唯一方法是每天坐下来工作', evidence_type: '个人经历', evidence: '作者和各种职业创作者的共同经验', source_section_id: 'overcome', strength: 'strong' }
  ],
  key_concepts: [
    { id: 'concept-1', term: '内阻力（Resistance）', definition: '一种阻止人做重要创造性工作的内在力量', explanation: '越重要的事越强，表现为拖延、恐惧、自我怀疑', examples: ['写作前先刷手机', '准备健身前突然想整理房间'], related_concepts: ['concept-2'], source_section_id: 'resistance-nature' },
    { id: 'concept-2', term: '职业选手心态', definition: '不管感觉如何都坐下来工作的态度', explanation: '把创作当成上班，定时定点', examples: ['每天早上9点坐在书桌前', '不管写得好不好先写够4小时'], related_concepts: ['concept-1'], source_section_id: 'overcome' }
  ],
  extended_reading: [
    { id: 'ext-1', topic: '习惯养成与创造力', context: '内阻力本质上是一种习惯问题', deep_dive: '养成每天创作的习惯是克服内阻力最实际的方法', related_concept_ids: ['concept-2'], further_resources: '可以参考原子习惯等书籍' }
  ],
  mind_map: {
    central_theme: '内阻力与职业选手',
    nodes: [
      { id: 'node-1', label: '内阻力是什么', type: 'theme', parent_id: null, detail: '一种反人类的创造性阻力' },
      { id: 'node-1-1', label: '特征：无形、不可协商', type: 'concept', parent_id: 'node-1', detail: '越重要越强' },
      { id: 'node-1-2', label: '表现：拖延、恐惧、自我怀疑', type: 'concept', parent_id: 'node-1', detail: '' },
      { id: 'node-2', label: '如何克服', type: 'theme', parent_id: null, detail: '成为职业选手' },
      { id: 'node-2-1', label: '每天坐下来工作', type: 'argument', parent_id: 'node-2', detail: '不等灵感' },
      { id: 'node-2-2', label: '穿过恐惧', type: 'argument', parent_id: 'node-2', detail: '怕了也做' }
    ]
  },
  quiz: {
    intro: '测测你的内阻力水平',
    questions: [
      { id: 'q1', text: '你有多少个"明天就开始"的计划？', type: 'choice', options: [{ label: '没有，说做就做', score: 0 }, { label: '1-2个', score: 1 }, { label: '3-5个', score: 2 }, { label: '数不清', score: 3 }] },
      { id: 'q2', text: '面对一件重要的事，你通常？', type: 'choice', options: [{ label: '立刻开始', score: 0 }, { label: '做点准备再说', score: 1 }, { label: '先查查资料', score: 2 }, { label: '先刷会手机', score: 3 }] }
    ],
    result_levels: [
      { max_avg_score: 1.0, level_label: '职业选手级', description: '你已经学会了和内阻力共处' },
      { max_avg_score: 2.0, level_label: '进阶中', description: '你意识到了内阻力，正在学习克服它' },
      { max_avg_score: 3.0, level_label: '业余选手', description: '内阻力是你的老朋友了，是时候跟它正面刚了' }
    ]
  },
  source_url: 'https://www.xiaoyuzhoufm.com/episode/674a16478d5d7e073a18b4cc'
}

exports.main = async (event, context) => {
  const results = []

  try {
    // 1. 尝试创建集合（已存在会报错，忽略）
    const collections = ['episodes', 'tasks', 'user_favorites', 'user_history']
    for (const name of collections) {
      try {
        await db.createCollection(name)
        results.push(`✅ 创建集合: ${name}`)
      } catch (e) {
        if (e.errCode === -502005 || (e.message && e.message.includes('already exists'))) {
          results.push(`⏭️ 集合已存在: ${name}`)
        } else {
          results.push(`❌ 创建集合失败 ${name}: ${e.message}`)
        }
      }
    }

    // 2. 检查测试数据是否已存在
    const existing = await db.collection('episodes').where({
      episode_id: TEST_EPISODE.episode_id
    }).get()

    if (existing.data && existing.data.length > 0) {
      results.push(`⏭️ 测试数据已存在 (episode_id: ${TEST_EPISODE.episode_id})`)
      return { success: true, results, episodeId: existing.data[0]._id }
    }

    // 3. 插入测试数据
    const doc = await db.collection('episodes').add({
      data: {
        ...TEST_EPISODE,
        created_at: db.serverDate()
      }
    })
    results.push(`✅ 插入测试数据: ${doc._id}`)

    return { success: true, results, episodeId: doc._id }
  } catch (e) {
    results.push(`❌ 错误: ${e.message}`)
    return { success: false, results, error: e.message }
  }
}
