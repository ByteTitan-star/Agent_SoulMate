import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { MessageCircle, Mic, Sparkles } from 'lucide-react';

export function HomePage() {
  return (
    <div className="max-w-5xl mx-auto px-4 py-16 md:py-24">
      <motion.section
        className="text-center mb-20"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <p className="text-soul-rose font-medium tracking-widest uppercase text-sm mb-4">与 AI 深度连接</p>
        <h1 className="font-display text-4xl md:text-6xl font-semibold text-soul-ink tracking-tight mb-6">
          创建你的
          <span className="block mt-1 bg-gradient-warm bg-clip-text text-transparent">灵魂伴侣</span>
        </h1>
        <p className="text-soul-deep/80 text-lg max-w-xl mx-auto leading-relaxed">
          自定义虚拟伴侣或朋友，用文字与语音进行真实对话，支持知识库与智能工具，让每一次交流都独一无二。
        </p>
      </motion.section>

      <motion.div
        className="grid md:grid-cols-3 gap-8 mb-16"
        initial="hidden"
        animate="visible"
        variants={{
          visible: { transition: { staggerChildren: 0.12 } },
          hidden: {},
        }}
      >
        {[
          {
            icon: Sparkles,
            title: '创建与分享',
            desc: '无限创建角色，设定姓名、性格、背景与专属音色，并发布到广场供他人使用。',
            to: '/create',
            cta: '去创建',
          },
          {
            icon: MessageCircle,
            title: '文字与语音',
            desc: '全双工语音对话，像打电话一样与角色交流；同时支持流畅的文本聊天。',
            to: '/plaza',
            cta: '选角色聊天',
          },
          {
            icon: Mic,
            title: '智能与知识',
            desc: '角色可绑定知识库（上传文档）并具备查天气、搜资讯等工具能力。',
            to: '/plaza',
            cta: '探索广场',
          },
        ].map((item) => (
          <motion.div
            key={item.title}
            variants={{
              hidden: { opacity: 0, y: 24 },
              visible: { opacity: 1, y: 0 },
            }}
            className="group relative p-6 rounded-2xl bg-white/70 border border-soul-sand/60 shadow-sm hover:shadow-md hover:border-soul-sage/40 transition-all duration-300"
          >
            <div className="w-12 h-12 rounded-xl bg-gradient-warm flex items-center justify-center text-white mb-4 group-hover:scale-105 transition-transform">
              <item.icon className="w-6 h-6" />
            </div>
            <h2 className="font-display text-xl font-semibold text-soul-ink mb-2">{item.title}</h2>
            <p className="text-soul-deep/70 text-sm leading-relaxed mb-4">{item.desc}</p>
            <Link
              to={item.to}
              className="inline-flex items-center text-soul-rose font-medium text-sm hover:underline"
            >
              {item.cta}
              <span className="ml-1">→</span>
            </Link>
          </motion.div>
        ))}
      </motion.div>

      <motion.div
        className="text-center"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
      >
        <Link
          to="/plaza"
          className="inline-flex items-center gap-2 px-8 py-3 rounded-full bg-soul-rose text-white font-medium hover:bg-soul-terracotta transition-colors shadow-lg shadow-soul-rose/20"
        >
          进入角色广场
          <span>→</span>
        </Link>
      </motion.div>
    </div>
  );
}
