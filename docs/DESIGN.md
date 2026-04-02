# Orchid Idea Generation: 详细研究设计

## 1. 研究目标

### 1.1 一句话问题定义

我们要解决的问题不是“让 LLM 生成看起来更好的 research idea”，而是：

**在 open-ended science ideation 场景下，如何让 LLM 生成更值得继续验证的 research ideas，使它们在 novelty、soundness、feasibility 和 grounding 上更强，并在后续验证或执行阶段更不容易崩掉。**

这里的重点是 idea 的 `downstream survivability`，而不是仅仅提高文本层面的流畅度、趣味性或整体印象分。

### 1.2 核心目标

Orchid 的目标是把 research ideation 从“单次文本生成问题”改写为“受证据、约束、偏好比较和预算共同影响的开放式搜索问题”。系统希望在 idea 生成阶段尽量减少以下几类高风险候选：

- 明显违背已有文献、常识或领域约束的 idea
- 看起来合理，但隐藏前提很多、稍一落实就失效的 idea
- 需要过高 compute、额外数据或隐含工程条件才能成立的 idea
- 文本上有新意，但经不起后续评审、验证或执行的 idea

### 1.3 评估目标的分层

论文中的评估目标不能再被写成一组彼此独立、完全正交的扁平指标，而应分成两层：

#### 第一层：上游 review factors

这些指标用于评估一个 idea 在文本和研究设计层面的质量。它们是我们公开展示的主要评估维度，但本质上更像若干 `latent factors`，并不严格正交。

- `Novelty`：idea 是否提出了有意义的新方向或新组合
- `Soundness`：idea 的逻辑是否自洽，论证链条是否成立
- `Feasibility`：idea 在现实资源、依赖和实现条件下是否有落地可能
- `Grounding / Verifiability`：idea 是否有足够证据支撑，关键主张是否可追溯、可验证

#### 第二层：下游 outcome metrics

这些指标不是文本 judge 应直接打出来的“想象型分数”，而是后续验证或执行环节中的真实结果。

- `Execution Success Rate`：在受控执行评估中，idea 是否更容易被后续 executor 跑通
- `Informative Outcome Rate`：最终实验是否产出有信息量的结果
- `End-to-End Yield`：总生成 ideas 中，最终变成 informative outcome 的比例

这个分层很重要。前四项是 judge 关注的上游因素，后三项是 downstream outcomes。论文必须避免把二者混成一个平铺评分表，否则评估会天然纠缠。

## 2. Motivation 与问题立项

### 2.1 当前 motivation 能否成立

能成立，而且是值得做的方向。

原始直觉是：现有 LLM ideation 系统可以生成很多看起来 novel 的想法，但这些想法一旦进入后续验证、实验设计、代码实现或真正执行阶段，就可能迅速暴露出不可行、条件不满足或风险过高的问题。这条主线是成立的，因为如果未来 AI for Scientist 的工作流越来越依赖“模型先提想法，再由 agent 或人类执行验证”，那么上游 ideation 的质量会直接决定后续试错成本。

但原稿里把问题根因过于简化成“LLM 没有有效参考已发表工作中的技术”，这不够稳。更合理的说法是：现有 ideation 系统的问题来自多个层面的失配，而不仅仅是参考文献不足。

### 2.2 更合理的问题根因分析

现有 ideation 系统 feasibility 不高，通常至少有四个层面的失配：

1. **文本质量与真实可行性失配**

很多系统优化的是 prose-level quality，例如 novelty、clarity、interestingness、overall score，但这些指标并不等价于“这个 idea 在真实研究条件下是否可验证、可执行、可产出信息量结果”。

2. **judge 信号与真实 downstream 成功失配**

LLM scalar score 往往高方差、低校准。一个 idea 文本得分更高，不代表它更可能在后续实验、代码实现或现实研究约束下成立。相比之下，pairwise preference 往往更稳定，也更接近“在若干候选中哪个更值得继续投入”的真实决策场景。

3. **search feedback 过于贫弱**

即使使用 preference-based search，如果反馈信号只是简单的 win-rate 或 winner/loser 数值，它也只能告诉系统“哪个更好”，却很难告诉系统“为什么更好、哪里有问题、下一步该改什么”。对于 open-ended ideation，这种反馈过于稀薄，无法充分支持真正的 refinement。

4. **retrieval 提供的是灵感，而不是约束**

很多 RAG ideation 工作把论文检索当作 inspiration source，但没有显式关注文献中的关键前提、依赖条件、失败模式、成本边界和适用范围。结果是 retrieval 只能减少明显胡说，却未必能提高真正的 feasibility。

### 2.3 为什么这个问题重要

如果这个问题被解决，价值不只是“judge 分更高”，而是整个自动科研流程的有效吞吐量提升。

更具体地说，意义体现在：

- 降低无效 idea 带来的后续试错成本
- 提高相同 token / compute 预算下最终获得有效结果的数量
- 让自动科研从“能生成很多 idea”迈向“能持续生成值得验证的 idea”
- 为未来更强的 AI for Scientist pipeline 提供一个更可靠的上游 ideation 组件

### 2.4 审稿人最可能的拒稿理由

如果这篇论文按粗糙版本直接写，最容易被拒的点有五个：

1. **feasibility 定义不清**

如果 feasibility 主要靠人类或 LLM 主观打分，而没有更强的有效性论证，审稿人会认为这只是“另一套 judge”。

2. **open-ended 主张与受控实验不一致**

如果论文声称做 open-ended science ideation，但实验其实只在一个很窄的受控 AI/ML 设定中完成，审稿人会质疑主张是否被过度放大。

3. **搜索只是复杂化的 rerank**

如果搜索部分没有清楚展示为什么它比“多生成一些 idea 再打分排序”更有效，那么 PB-MCTS 或其他 search 机制会被认为只是增加复杂度。

4. **judge protocol 缺少有效性证明**

如果大规模结论主要来自 multi-LLM-as-a-judge，但论文没有证明 judge 强度、去偏策略和人类/执行对齐关系，整篇论文会被认为建立在脆弱的代理指标上。

5. **baseline 与评估不公平**

如果 baseline 复现不稳、token budget 不一致、judge 不统一，实验结论会缺乏说服力。

## 3. 论文主张与范围

### 3.1 论文主张

这篇论文的主张应明确为：

**相比主要优化 novelty 或文本质量的 ideation 系统，Orchid 通过 evidence-grounded idea construction、language-augmented preference search，以及更严格的 judge-centric evaluation protocol，在 open-ended science ideation 设定下生成更值得继续验证的 research ideas。**

更谨慎一点地说，这篇论文不主张“我们直接解决了开放科学研究的自动执行问题”，而是主张：

- 我们提升了 idea 在早期阶段的质量与可信度
- 我们提高了这些 ideas 在后续验证环节中存活下来的概率
- 当把开放研究范围收窄到可控子任务时，我们的方法也更容易产出可执行的 ideas
- 即使 execution 实验规模有限，大规模的 multi-LLM judge protocol 也能提供有说服力的主评估证据，前提是其有效性被充分验证

### 3.2 范围边界

主任务必须写成 `open-ended science ideation`，而不是一开始就把任务定义成 bound 的 benchmark 或 starter repo 改进问题。

也就是说，Orchid 的输入首先应该是一个开放的研究范围、方向或问题空间，例如：

- 一个开放 scientific topic
- 一个 broad research question
- 一个尚未被固定为单一 repo/单一 benchmark 的研究方向

但当我们要做 **可控、可复现、可比较** 的 execution evaluation 时，可以在评估协议中临时收窄这个开放研究范围，把它实例化成更可操作的 AI/ML 子任务，并提供统一的数据、资产、starter repo 或预算。

这点必须写清楚：

- `open-ended` 是主任务定义
- `bounded execution setting` 是后验验证协议
- 后者服务于可控评估，不应反过来改写前者的任务定义

## 4. 方法设计

### 4.1 总体方法概述

方法部分不应依赖于某几个固定数据结构的命名，而应从高层逻辑说明 Orchid 做了什么。

总体上，Orchid 包含两层核心机制：

1. `evidence-grounded idea construction`
2. `language-augmented preference search`

第一层负责让 idea 不只是“像一个研究想法”，而是尽可能建立在可追溯、可验证、与当前问题相关的证据基础上。第二层负责在多个候选之间进行比较、修正和搜索，避免系统只做一次性 generate-rank。

系统的最终输出不是某种必须固定格式的数据结构，而是一组经过证据支撑、风险分析与偏好比较后的高质量 research ideas。具体实现时可以有不同表示方式，但论文里不应把贡献绑定到某个字段设计上。

### 4.2 Evidence-Grounded Idea Construction

#### 设计目标

这一层的目标不是简单做 paper retrieval，而是把开放研究问题与已有证据联系起来，使模型在生成 idea 时显式考虑：

- 相关领域已有工作到底做到了什么
- 哪些机制或方向有正面证据支持
- 哪些方向存在失败先例、强依赖条件或高风险假设
- 当前 idea 的核心假设是否已经与文献或现实约束冲突

#### 关键思想

原稿提到一个非常真实的问题：每篇论文结构差异很大，几乎不可能事先定义一套固定字段，要求模型从所有论文中统一抽取。这个判断是对的。

因此，Orchid 的 retrieval 与证据构建不应被表述为“对每篇论文做固定模板抽取”，而应表述为：

- 围绕当前研究范围建立背景证据
- 围绕当前候选 idea 进行针对性检索
- 重点关注 assumptions、dependencies、risks、failure modes、applicability，而不是只摘录结论段或创新点

#### 为什么这层可能有效

因为很多“看起来不错但最终跑不通”的 idea，并不是纯粹由于模型没有想象力，而是因为模型没有显式处理以下问题：

- 这个思路成立需要哪些前提
- 当前问题设定是否满足这些前提
- 相似方法曾在哪些条件下失败
- 所谓的 improvement 是否发生在一个和当前设定根本不同的场景

如果这些内容能在 ideation 阶段被更充分地看见，系统就更可能生成 grounded 且 feasible 的想法。

#### 设计要点

- 主实验中不应依赖实时 web 搜索来支撑核心结论，最好使用 frozen literature snapshot
- “up-to-date” 更稳的写法是 “recency-aware under a fixed cutoff”
- retrieval 的价值不在于“搜得多”，而在于“能否捕捉对 feasibility 真正重要的约束”

### 4.3 Language-Augmented Preference Search

#### 为什么不能照搬 PB-MCTS

PB-MCTS 的核心直觉是对的：pairwise comparison 往往比 pointwise score 更可靠，尤其是在 idea 质量这种高噪声对象上。

但如果把 PB-MCTS 原封不动搬到 Orchid 上，会遇到一个关键问题：其反馈信号过于数值化。简单的 win-rate 或 winner/loser 只能表达“哪个候选更好”，却几乎不提供足够丰富的上下文来支持下一步 refinement。

对于 open-ended science ideation，这种反馈不够。因为这里真正困难的不是只做选择，而是：

- 找出当前 idea 的关键漏洞
- 判断漏洞是证据不足、逻辑跳跃，还是实现依赖不现实
- 告诉系统下一轮该修哪里，而不是只告诉它“输了”

因此 Orchid 的 tree search 不能完全按 PB-MCTS 那篇论文来，一定要改成更适合任务的 `language-augmented preference search`。

#### 搜索中的 judge 应输出什么

在 Orchid 中，search-time judge 不应只输出一个 pairwise winner，而应至少输出三类信息：

- 哪个 idea 当前更值得继续探索
- 这一判断的核心原因是什么
- 下一步最值得修补、验证或删减的内容是什么

也就是说，search-time feedback 必须包含 `pairwise preference + natural-language critique + state update signal`。

这里的自然语言反馈不是可有可无的解释文本，而是搜索状态更新的重要输入。系统需要根据这些 critique 去决定下一轮如何扩展候选，例如：

- 补充被忽略的 assumptions
- 缩窄过强或过泛的 claim
- 追加对关键机制的证据检索
- 剪掉资源或依赖明显不现实的分支

#### search 的意义是什么

search 的意义不在于“树结构很复杂”，而在于：

- 允许系统并行保留多个候选方向
- 让系统能够在迭代中补齐 assumptions、削弱高风险点、重组已有想法
- 让系统不只依赖一次采样运气，而是在预算内更系统地探索候选空间

PB-MCTS 可以继续作为概念起点，但论文必须明确：Orchid 的创新不在“直接复用 PB-MCTS”，而在“把 pairwise reliability 与 context-rich natural-language feedback 结合起来，使 search 真正适合 ideation refinement”。

#### 如果搜索效果不明显怎么办

这是必须提前考虑的风险。

如果 language-augmented tree search 相比更简单的 iterative refine 没有明显收益，论文也不应整体失效。此时可以把叙事收敛为：

- evidence-grounded ideation 是主要增益来源
- preference signal 提供更稳的选择机制
- 自然语言 critique 至少为 refinement 提供可解释更新
- tree search 只是当前较强的一种实现，而不是全部贡献所在

### 4.4 Search-Time Judge 与 Final-Evaluation Judge 的分工

论文中必须明确区分两种 judge 协议，否则方法和评估会混在一起。

#### Search-Time Judge

服务于 tree search，目标是驱动候选扩展与修正。它的核心输出是：

- pairwise preference
- 自然语言 critique
- 下一步 state update 的方向

这类 judge 不追求绝对、公平、全局排序，它更像一个高质量 reviewer，负责告诉系统“接下来该怎么改”。

#### Final-Evaluation Judge

服务于最终 reranking、baseline 对比和论文报告。它的目标不是指导搜索，而是尽可能公平、稳定地比较不同方法生成的候选。

因此 final-evaluation protocol 应该：

- 使用 blind pairwise comparison，而不是直接相信 search-time win-rate
- 隐藏方法名
- 随机化输入顺序
- 尽量控制长度和格式偏差
- 对 pairwise 结果做聚合与去偏，而不是直接取单次判断

这一层更适合采用 `multi-LLM-as-a-judge`，而不是单模型、单次、单分数的评估方式。

### 4.5 方法为什么可能有效

方法层面的核心逻辑应被写成一个闭环：

- retrieval 不是为了让输出更像论文，而是为了让系统更早看到关键约束
- pairwise preference 不是为了提供另一个分数，而是为了提供更稳的选择信号
- 自然语言 critique 不是为了写解释，而是为了驱动真正的 refinement
- final evaluation 不直接复用 search signal，而是通过去偏的 pairwise judging 做公平比较

如果这四点立住，Orchid 的方法才会显得是“为了解决 feasibility 问题而设计”，而不是若干热门模块的拼接。

## 5. 方法设计的合理性与潜在问题

### 5.1 当前方法设计合理吗

整体方向是合理的，尤其是在以下三个判断上：

1. 只优化 novelty 或 prose quality 不够
2. feasibility 改善不能只靠一次性打分或人工复查
3. search 的反馈不能只靠数值型 win-rate

但当前方法部分需要注意一个原则：**论文应把重点放在机制与逻辑上，而不是某种固定 schema。**

### 5.2 当前方法中必须澄清的点

虽然不应该依赖具体数据结构，但下面这些问题必须在论文中说清楚：

- 输入给系统的“研究范围”具体是什么粒度
- retrieval 如何从 broad topic 走向 idea-specific evidence
- search-time judge 的自然语言反馈如何进入下一轮搜索
- final-evaluation judge 如何去偏、聚合并形成最终排序
- feasibility 主要由哪些 observable signals 支撑
- 候选 ideas 如何去重与筛选

### 5.3 预计方法能否产生效果

在合理设定下，这个方法有较大概率有效，但更可能出现的是“结构性提升”，而不是“所有指标全面碾压”。

更现实的预期是：

- `Feasibility` 与 `Grounding` 提升明显
- `Overall Preference` 在强 judge 协议下提升明显
- `Execution Success Rate` 与 `Informative Outcome Rate` 在受控子集上提升明显
- `Novelty` 保持基本持平，或有轻微回落但不显著

这其实是可以接受的结果，因为论文主张本来就不是“比所有方法都更 novel”，而是“在不明显牺牲 novelty 的前提下提高 ideas 的 downstream survivability”。

### 5.4 如果方法没有产生效果，可能是什么原因

#### 情况一：judge 认为更 feasible，但执行并没有改善

可能原因：

- judge 学到的是 prose plausibility，而不是实际 feasibility
- 公开指标与真实 downstream outcome 的相关性不够强

修正方向：

- 引入更贴近执行的辅助信号
- 强化 judge factor 与 execution outcome 的 calibration

#### 情况二：retrieval 增强了 grounding，但 novelty 明显下降

可能原因：

- 系统过于依赖已有文献，导致保守化
- feasibility 信号权重过高

修正方向：

- 明确加入 novelty floor
- 改成在 novelty 和 feasibility 之间做 Pareto-style 选择，而不是单一加权和

#### 情况三：search 比简单 baseline 没明显优势

可能原因：

- 候选空间本身不够复杂
- 自然语言 critique 没有真正进入状态更新
- 搜索策略没有真正修正 ideas，只是在重复采样

修正方向：

- 减弱对特定 search 算法的依赖
- 把贡献重新收束到 evidence grounding 和 preference-driven refinement

#### 情况四：judge 结果本身不稳定

可能原因：

- judge 模型能力不够强
- 单模型偏见太大
- prompt 没有隔离不同评估因子

修正方向：

- 使用近期 frontier closed models 作为 judge 池
- 做 multi-judge aggregation
- 重写 review prompt，使 latent factors 尽可能被分开考察

## 6. 评估协议设计

### 6.1 评估总原则

每个实验都必须回答一个明确问题，并且该实验的指标真的能验证这个问题。

对于 Orchid，这里还有一个额外现实：`multi-LLM-as-a-judge` 目前是唯一能大规模、批量、统一评估 ideas 的方法。因此，judge protocol 不是附属实验，而是论文的核心基础设施之一。

这意味着：

- 如果 execution 实验走得通，它是强外部证据
- 如果 execution 实验走不通，大规模 judge protocol 仍然必须能独立支撑主要结论
- 因此 judge protocol 的有效性本身必须进入主实验，而不是放在附录里

### 6.2 指标体系：Latent Factors 与 Downstream Outcomes

`Novelty / Soundness / Feasibility / Grounding` 这四个公开指标不应被当作完全正交的平铺项目，而应被视为若干上游 latent factors。

更准确地说：

- `Novelty` 与 `Feasibility` 天然有张力
- `Soundness` 与 `Grounding` 往往相互影响
- `Feasibility` 往往会受到 `Grounding` 和假设负担的影响

因此论文不能宣称“我们设计了一组完全独立的指标”，而应宣称：

- 我们通过 prompt design 尽量减少它们之间的污染
- 我们把 execution metrics 留给 downstream outcome 层
- 我们通过 calibration study 检查上游 latent factors 是否真的能预测 downstream success

### 6.3 Review Prompt 应该如何尽量正交

虽然这些指标不可能完全正交，但 review prompt 可以尽量减少混淆。设计原则应至少包括以下几点：

1. **每个指标只回答一个窄问题**

- `Novelty`：这个想法相对已知工作是否有实质性新意
- `Soundness`：在其自身假设下，逻辑链条是否成立
- `Feasibility`：忽略它是否有趣，只看资源、依赖和实现路径是否现实
- `Grounding`：忽略写作好坏，只看关键主张是否有证据支持、是否可验证

2. **显式加入 anti-leak 指令**

评 `Novelty` 时，要求 judge 不因为“很难实现”而压分。

评 `Feasibility` 时，要求 judge 不因为“很有创意”而放宽标准。

评 `Grounding` 时，要求 judge 不因为文风流畅而高估证据支撑。

评 `Soundness` 时，要求 judge 只看逻辑闭环和假设一致性。

3. **先做因子分析，再做总体偏好**

不要一开始就问 “overall 好不好”。更稳的协议是：

- 先让 judge 分别分析上游因子
- 再单独问一个总体问题：`哪个 idea 更值得获得下一步验证预算`

这样可以减少总体偏好过早污染各个因子判断。

4. **不要让 judge 直接打 execution outcome**

`Execution Success Rate`、`Informative Outcome Rate`、`End-to-End Yield` 不是文本 judge 应直接预测的标签。它们最多只能作为：

- 小规模 execution 实验中的真实结果
- judge calibration study 的目标变量

5. **保留公开指标名，但内部拆成更基础判据**

论文主表可以继续用 `Novelty / Soundness / Feasibility / Grounding` 这组名字，方便读者理解。

但 judge prompt 内部应进一步拆成更基础的问题，例如：

- 是否只是常见套路重组
- 是否依赖未说明的关键前提
- 是否需要不现实的资源
- 是否给出了可追溯的 supporting evidence

### 6.4 Judge 协议的两层设计

#### Search-Time Judge

tree search 阶段，judge 协议应采用：

- pairwise comparison
- 自然语言 critique
- 针对下一轮 refinement 的更新建议

这里的目标是推动搜索，不追求全局公平排序。

#### Final-Evaluation Judge

最终对 baseline 和候选进行比较时，judge 协议应采用：

- blind pairwise judging
- 双向顺序随机化
- 方法名隐藏
- 格式与长度尽量标准化
- 多 judge 聚合

为了减少单次判断噪声，最终排序不应直接用单场 win-rate，而应通过成对比较矩阵和去偏聚合来形成更稳的 ranking。

### 6.5 Judge 模型选择

根据目前经验，评估 idea 好坏所需的大模型能力门槛很高。弱模型往往会：

- 被文风带偏
- 无法区分真正的新意和表面花哨
- 无法识别复杂的 hidden assumptions
- 无法稳定比较 high-level research ideas

因此，论文默认应采用 `recent frontier closed models` 作为 judge 池，而不是默认单模型或弱模型。

这里最好把 “judge strength matters” 作为显式实验结论去验证，而不是只写成经验判断。

## 7. 实验设计

### 7.1 实验结构

整篇论文至少需要覆盖五类实验：

1. 主对比实验：在 open-ended ideation 任务中，Orchid 是否整体更强
2. judge validity 实验：多 LLM 评估协议是否可信
3. judge strength 实验：强 judge 是否显著优于弱 judge
4. execution calibration 实验：上游 judge 结果是否与小规模 downstream outcome 对齐
5. ablation：哪些模块在起作用，为什么起作用

### 7.2 主对比实验

#### 要验证什么

验证 Orchid 是否在 open-ended ideation 任务中，整体上生成了更高质量、也更值得继续验证的 ideas。

#### 对比对象

采用 reproducible-first baseline policy。主表建议保留：

1. `Raw Backbone LLM`
2. `Retrieval-Only Baseline`
3. `Self-Refine / Reviewer Loop Baseline`
4. `Score-Based Search Baseline`
5. `1-2 个可公平复现的 literature systems`
6. `Orchid`

对于你原稿中列出的 DeepInnovator、CoI-Agent、ResearchAgent、Scimon、SciAgents、IRIS，不应默认全部进入 head-to-head。只有满足以下条件的方法才进入主表：

- 可复现
- 可在相近 backbone 与预算下公平对齐
- 其设计目标与本工作真正可比

其余方法更适合作为 qualitative reference 或 related work。

#### 评估协议

主表应基于 `final-evaluation multi-LLM-as-a-judge` 完成，而不是简单 pointwise 单模型打分。

更合理的流程是：

- 先对候选 ideas 做 blind pairwise comparison
- 再由多 judge 给出 factor-aware 的短理由
- 最后聚合得到 `Overall Preference` 和公开指标结果

#### 指标

主实验建议公开报告以下 idea-level 指标：

- `Novelty`
- `Soundness`
- `Feasibility`
- `Clarity`
- `Grounding / Verifiability`
- `Overall Preference`

这里的重点不是假装这些指标完全独立，而是通过 prompt 设计尽量减少它们之间的污染。

#### 结果呈现形式

主结果建议使用：

- 一个主表：报告均值、标准差和显著性比较
- 一个 pairwise ranking 或 Bradley-Terry / Elo 风格的总体排序图
- 一个 Pareto 图：横轴 novelty，纵轴 feasibility 或 judge-derived overall preference

不建议把雷达图作为主图，因为它不利于精确比较，也不容易支撑论文的关键论点。

### 7.3 Judge Validity 实验

#### 要验证什么

验证 multi-LLM-as-a-judge 是否真的是一个可 defended 的主评估协议。

#### 至少要做的验证

1. **Human alignment**

对分层采样得到的 idea pairs，请人类专家标注哪个更值得继续验证，并比较 judge 与 human majority 的一致性。

2. **Judge strength matters**

比较 frontier judge 与较弱 judge 的表现差异，证明高质量 judge 对 idea evaluation 是必要条件。

3. **Single vs Multi Judge**

比较单一 judge 与 multi-judge aggregation 的稳定性和偏差。

4. **Debiasing effectiveness**

比较有无 blind、顺序随机化、长度控制、方法名隐藏时结果的变化。

#### 指标

建议至少报告：

- `Pairwise Accuracy against Human Majority`
- `Inter-Judge Agreement`
- `Inter-Rater Agreement`
- `Ranking Stability`
- `Position / Length Bias Sensitivity`

### 7.4 Execution Calibration 实验

#### 要验证什么

验证 judge 的上游 latent factors 是否真的与 downstream success 有关系。

#### 设计

execution 实验在这篇论文里更适合被写成 `calibration / external validity` 层，而不是唯一主轴。

对每个方法：

- 先在 open-ended 设定下生成一批 ideas
- 从中选出去重后的 `top-K` ideas
- 将对应研究范围收窄成一个统一、可执行的 AI/ML 子任务
- 在相同 starter repo、相同预算、相同 executor、相同 retry policy 下进行执行验证

#### 关键指标

- `Run Success Rate`
- `Experiment Completion Rate`
- `Informative Outcome Rate`
- `Execution Success Rate`
- `End-to-End Yield`
- 上游 latent factors 与这些 outcome 的相关性

#### 如果 execution 实验不稳定怎么办

如果 execution 部分成本高、噪声大、难以完全跑通，那么它至少仍应保留为：

- 小规模 calibration study
- 失败案例分析
- 对 judge validity 的外部 sanity check

换句话说，execution 是强证据，但论文不能把所有可发表性都押在 execution 上。

### 7.5 Token Efficiency 实验

#### 要验证什么

验证 Orchid 是否在相同 token 开销下，更高效地产生“值得继续投入”的 ideas。

#### 更合适的指标定义

比起“生成一个多少分以上的 idea 需要多少 token”，更贴近论文主张的对象是：

- 生成一个 `high-preference idea` 需要多少 token
- 生成一个 `high-feasibility idea` 需要多少 token
- 生成一个 `execution-successful idea` 需要多少 token
- 生成一个 `informative outcome` 需要多少 token

#### 结果呈现

建议画 budget-efficiency 曲线：

- 横轴：目标阈值或 target yield
- 纵轴：平均 token 成本

### 7.6 Ablation

ablation 必须围绕“哪个模块为什么提升了 feasibility 与 downstream survivability”来设计，而不是只堆很多配置。

建议最少做以下几组：

1. `w/o retrieval`

验证检索是否真的提高 constraint awareness，而不是只让 wording 更像论文。

2. `unstructured retrieval snippets` 替代更强的 evidence construction

验证简单塞论文片段，是否不如围绕 assumptions、dependencies 和 failure modes 的证据构建。

3. `numeric preference only` 替代 `preference + natural-language critique`

验证 context-rich feedback 是否真能改善 search，而不是只靠 win-rate。

4. `w/o preference-based selection`

把 pairwise preference 换成 scalar score selection，验证 preference signal 的必要性。

5. `shallow search / width=1`

验证 branching exploration 是否比单链 refinement 更有效。

6. `weak judge pool` 替代 `frontier judge pool`

验证强 judge 对 idea evaluation 的必要性。

7. `flat rubric prompt` 替代 `factor-isolated prompt`

验证将 latent factors 尽量拆开的 prompt 设计是否确实更稳。

#### ablation 结果呈现

建议统一用表格呈现，并尽量包含以下三类结果：

- judge-level quality 指标
- ranking stability
- 与 execution calibration 的相关性

### 7.7 Case Study

case study 不应只是“展示搜索树长什么样”，而应展示：

- 一个成功 idea 如何在 evidence 和 critique 中逐渐变得更稳
- 一个失败 idea 如何因为 hidden assumptions、依赖缺失或资源不现实而被降权
- 自然语言 feedback 如何具体改变了下一轮 refinement

最好的展示形式是：

- 一个树状或轨迹式演化图
- 一个 refinement 前后对照
- 一个 failure taxonomy 示例

## 8. 结果预期与风险分析

### 8.1 预期结果

最合理的预期结果不是“所有维度全面碾压”，而是：

- Orchid 在 `Feasibility`、`Grounding / Verifiability` 和 `Overall Preference` 上显著提升
- `numeric preference only` 相比 `preference + natural-language critique` 明显更弱
- frontier judge 相比弱 judge 更稳定、与人类更一致
- bounded execution calibration 中，Orchid 的上游评估结果对 downstream outcomes 具有更强预测力
- Orchid 在 `Novelty` 上与强 novelty baseline 基本持平，或略有下降但不显著

这类结果是可以接受的，因为论文要证明的不是“最天马行空”，而是“更值得继续验证和投入”。

### 8.2 最关键风险

#### 风险一：judge protocol 被认为只是更复杂的代理指标

应对方式：

- 把 judge validity study 放进主实验而不是附录
- 证明 strong judge、multi-judge 和 debiasing 都是必要的
- 证明 judge 结果与 execution calibration 至少有正相关

#### 风险二：execution benchmark 噪声大

应对方式：

- 固定 executor、预算、retry policy
- 做 failure taxonomy
- 报告 execution 仅作为 external validity，而不是整篇论文唯一支柱

#### 风险三：open-ended 主张和 execution 子实验之间的口径冲突

应对方式：

- 在论文里明确区分主任务与后验验证协议
- 不把 execution 子实验包装成对全部 open-ended science 的直接证明

#### 风险四：方法增益主要来自 retrieval，而不是 search

这不一定会让论文失效。只要论文主张写得准确，即“evidence-grounded ideation 显著提升了 downstream survivability，而 language-augmented preference search 进一步放大这一增益”，贡献仍然成立。只是需要降低对特定 tree search 实现的叙事权重。

#### 风险五：公开指标之间仍然纠缠

这在理论上很难完全避免，因此不要把论文写成“我们发明了完全正交的指标体系”。更稳的写法是：

- 我们承认这些指标存在依赖关系
- 我们通过 factor-isolated prompt 尽量减少污染
- 我们最终用 downstream calibration 来检验这些 factor 是否有意义

## 9. 论文中应如何组织叙事

### 9.1 引言叙事

引言建议按以下逻辑展开：

1. LLM 已经能够生成看起来 novel 的 research ideas
2. 但 ideation-time quality 不等于 downstream-time success
3. 当前系统更多优化 novelty、quality、diversity，而非 downstream survivability
4. open-ended science ideation 中最难的不是“生成更多 idea”，而是“生成更值得继续验证的 idea”
5. Orchid 通过 evidence grounding、language-augmented preference search 和更严格的 judge protocol 改善这一点

### 9.2 方法叙事

方法部分必须做到从总体到局部：

1. 先定义目标：提升 open-ended ideation 的 idea quality 与 downstream survivability
2. 再说明 evidence grounding 与 language-augmented preference search 分别解决什么问题
3. 明确 search-time judge 和 final-evaluation judge 的分工
4. 最后再写实现细节，而不是一上来定义一堆 schema

### 9.3 实验叙事

实验部分按下面顺序最自然：

1. 主对比：open-ended ideation 整体是否更强
2. judge validity：主评估协议是否可信
3. execution calibration：上游评估是否能对齐 downstream outcome
4. ablation：为什么有效
5. case study：系统到底如何利用 critique 修正 idea

## 10. 当前版本的最终结论

当前课题方向是值得做的，而且有潜力形成一篇逻辑更自洽的 open-ended science ideation 论文。

但要成立，必须守住以下五点：

1. 把主任务明确定义为 `open-ended science ideation`
2. 把 retrieval 从“知识增强”改写为“与 feasibility 相关的证据构建”
3. 把 search 从“PB-MCTS with win-rate”改写为“language-augmented preference search”
4. 把 `multi-LLM-as-a-judge` 写成主评估协议之一，并充分论证其有效性
5. 把 `Novelty / Soundness / Feasibility / Grounding` 写成上游 latent factors，把 execution 指标写成 downstream outcomes

只要这五点立住，Orchid 的方法与实验就能形成更自然的闭环；否则论文很容易在“搜索到底改进了什么”“judge 到底是否可信”“这些指标到底有没有意义”这几个问题上被审稿人击穿。
