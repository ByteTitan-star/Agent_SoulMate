"""生成家庭医生角色可上传的知识库 PDF。"""

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate

FONT_PATH = r'C:\Windows\Fonts\simhei.ttf'
OUT_PATH = Path(__file__).resolve().parents[2] / 'docs' / '家庭医生安然_健康知识库.pdf'


def main() -> None:
    pdfmetrics.registerFont(TTFont('SimHei', FONT_PATH))
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='CNTitle', fontName='SimHei', fontSize=18, leading=26, spaceAfter=14))
    styles.add(ParagraphStyle(name='CNH1', fontName='SimHei', fontSize=14, leading=22, spaceBefore=14, spaceAfter=8))
    styles.add(ParagraphStyle(name='CNH2', fontName='SimHei', fontSize=12, leading=20, spaceBefore=10, spaceAfter=6))
    styles.add(ParagraphStyle(name='CNBody', fontName='SimHei', fontSize=10.5, leading=18, spaceAfter=6))
    styles.add(
        ParagraphStyle(name='CNNote', fontName='SimHei', fontSize=9.5, leading=16, textColor='#444444', spaceAfter=8)
    )

    story = []

    def add(text: str, style: str = 'CNBody') -> None:
        story.append(Paragraph(text.replace('\n', '<br/>'), styles[style]))

    add('家庭医生安然 · 健康知识库（演示用）', 'CNTitle')
    add('适用角色：家庭医生/健康顾问「安然」', 'CNNote')
    add(
        '声明：本文件仅供科普与就医引导演示，不能替代执业医师面诊、检查、诊断或处方。'
        '出现紧急情况请立即拨打急救电话或前往急诊。',
        'CNNote',
    )

    add('一、使用说明（给 AI 检索）', 'CNH1')
    add(
        '当用户描述不适时，优先匹配本知识库中的「常见场景」「红旗症状」「居家观察」「何时就医」段落，'
        '用通俗语言回答，并强调信息不足时不要下定论。'
    )
    add('回答应避免开具具体处方药剂量；可提示“需由医生评估后用药”。')

    add('二、问诊信息收集清单', 'CNH1')
    add(
        '建议引导用户补充：1）主要症状与部位；2）开始时间与变化；3）诱因（受凉、饮食、劳累、外伤等）；'
        '4）伴随症状（发热、呕吐、胸闷、皮疹等）；5）基础病与过敏史；6）正在服用的药物；'
        '7）怀孕/备孕/哺乳情况；8）近期旅行或传染病接触史。'
    )

    add('三、紧急红旗症状（优先急诊）', 'CNH1')
    add('3.1 循环与呼吸', 'CNH2')
    add(
        '突发严重胸痛/压榨感并向左臂、下颌放射；呼吸困难、口唇发紫；大咯血；晕厥或意识不清；'
        '一侧肢体无力、口角歪斜、言语困难（疑似中风）。'
    )
    add('3.2 出血与外伤', 'CNH2')
    add('无法止住的大出血；头部外伤后剧烈头痛、反复呕吐、嗜睡；严重烧伤；可疑骨折伴肢体畸形或远端苍白冰凉。')
    add('3.3 过敏与感染', 'CNH2')
    add('全身风团伴喉头紧、喘鸣；高热伴颈强直、皮疹、精神萎靡；婴儿拒食、持续高热、抽搐。')
    add('3.4 精神心理危急', 'CNH2')
    add('明确自杀/自伤计划或正在实施；严重幻觉妄想导致危险行为。应建议立即寻求紧急专业帮助。')

    add('四、常见场景科普', 'CNH1')

    add('4.1 普通感冒与流感样症状', 'CNH2')
    add('常见表现：鼻塞流涕、咽痛、轻中度咳嗽、低热或中热、乏力。多数为自限性，休息、补水、对症处理为主。')
    add('居家观察：体温变化、饮水与尿量、呼吸是否顺畅、是否出现胸痛或血痰。')
    add('建议就医：高热超过3天不退；呼吸急促；原有慢阻肺/哮喘明显加重；老人、婴幼儿、孕妇症状进展快。')

    add('4.2 急性肠胃炎样不适', 'CNH2')
    add('常见表现：恶心呕吐、腹痛、腹泻，可能与不洁饮食有关。重点是防脱水。')
    add('居家建议：少量多次补液；清淡饮食；观察尿量与精神状态。')
    add('建议就医：持续剧烈腹痛；便血/黑便；高热；明显脱水（口干、尿少、头晕）；孕妇或慢性病患者症状重。')

    add('4.3 头痛', 'CNH2')
    add('紧张性头痛常见于压力与睡眠不足；偏头痛可有搏动性疼痛、畏光畏声。突然“一生中最剧烈”的头痛需警惕急症。')
    add('建议就医：突发爆炸样头痛；头痛伴发热颈强直；头痛伴神经功能缺损；头部外伤后进行性加重。')

    add('4.4 失眠与节律紊乱', 'CNH2')
    add('睡眠卫生：固定起床时间、午后少咖啡因、睡前减少屏幕刺激、卧室偏暗偏凉、白天适度运动。')
    add('短期失眠可先调整作息与压力源；长期失眠、白天功能受损或伴情绪低落，建议线下评估，不自行长期依赖镇静催眠药。')

    add('4.5 焦虑相关躯体化', 'CNH2')
    add('可表现为心慌、胸闷、出汗、胃肠不适。需先排除急症心脏/肺部问题的红旗症状。')
    add('缓解思路：规律作息、呼吸放松、减少咖啡因、适度运动；持续影响生活时建议心理/精神科评估。')

    add('4.6 血压与代谢管理（科普）', 'CNH2')
    add('高血压管理强调：限盐、控体重、规律运动、戒烟限酒、遵医嘱用药与监测，不因“感觉没事”自行停药。')
    add('血糖管理强调：饮食结构、运动、体重、足部与视力随访；低血糖要会识别（出汗、心慌、手抖、意识改变）。')

    add('五、居家护理通用原则', 'CNH1')
    add('1）先安全：有红旗症状先急诊，不要硬扛。')
    add('2）先观察：记录体温、症状时间线、诱因与缓解因素，方便就医描述。')
    add('3）先基础：睡眠、水分、营养、适度活动往往比“到处找偏方”更重要。')
    add('4）用药谨慎：不随意合用多种感冒药；不把抗生素当万能药；儿童与孕妇用药必须更谨慎。')
    add('5）传染病防护：发热呼吸道症状期间减少聚集，戴口罩，勤洗手。')

    add('六、就医沟通话术模板', 'CNH1')
    add('建议用户按以下结构向医生说明：')
    add('“我主要是……（症状），从……开始，加重/缓解情况是……；伴随……；既往有……；对……过敏；正在服用……；我最担心的是……。”')

    add('七、角色回答示例边界', 'CNH1')
    add('正确：根据描述给出可能方向与观察建议，并列出何时就医。')
    add('错误：直接说“你就是某病”、给出具体处方剂量、或鼓励延误急诊。')
    add('信息不足时模板：目前信息还不够判断，建议补充……；若出现……请马上就医。')

    add('八、关键词索引（便于检索）', 'CNH1')
    add(
        '急诊红旗；胸痛；呼吸困难；中风；过敏性休克；高热；脱水；感冒；流感；腹泻；头痛；失眠；'
        '焦虑；高血压；血糖；孕妇；婴幼儿；老人；用药安全；就医话术。'
    )

    doc = SimpleDocTemplate(
        str(OUT_PATH),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title='家庭医生安然_健康知识库',
        author='AgentSoulMate Demo',
    )
    doc.build(story)
    print(f'OK {OUT_PATH}')
    print(f'SIZE {OUT_PATH.stat().st_size}')


if __name__ == '__main__':
    main()
