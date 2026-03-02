import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import clsx from 'clsx';
import { charactersApi } from '@/api/characters';
import type { CreateCharacterPayload } from '@/api/characters';
import { useAuth } from '@/context/AuthContext';

const GENDERS: { value: 'male' | 'female' | 'other'; label: string }[] = [
  { value: 'female', label: '女' },
  { value: 'male', label: '男' },
  { value: 'other', label: '其他' },
];

export function CreateCharacterPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [name, setName] = useState('');
  const [gender, setGender] = useState<'male' | 'female' | 'other'>('female');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [openingMessage, setOpeningMessage] = useState('');
  const [personality, setPersonality] = useState('');
  const [isPublic, setIsPublic] = useState(false);
  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleAvatarChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setAvatarFile(file);
    setAvatarPreview(URL.createObjectURL(file));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!user) {
      setError('请先登录后再创建角色');
      return;
    }
    if (!name.trim()) {
      setError('请填写角色名称');
      return;
    }
    if (!systemPrompt.trim()) {
      setError('请填写角色背景与设定（系统提示词）');
      return;
    }
    setSubmitting(true);
    const payload: CreateCharacterPayload = {
      name: name.trim(),
      gender,
      system_prompt: systemPrompt.trim(),
      opening_message: openingMessage.trim(),
      personality: personality.trim() ? personality.trim().split(/[,，、\s]+/).filter(Boolean) : [],
      is_public: isPublic,
      avatar_file: avatarFile ?? undefined,
    };
    try {
      const created = await charactersApi.create(payload);
      navigate(`/chat/${created.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建失败，请检查登录状态或稍后重试');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="h-full overflow-y-auto scrollbar-soft">
      <div className="max-w-2xl mx-auto px-4 py-10">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className="font-display text-3xl font-semibold text-soul-ink mb-2">创建角色</h1>
          <p className="text-soul-deep/70">设定名称、性别、背景与性格，并可选头像与公开分享</p>
        </motion.div>

        <motion.form
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
          onSubmit={handleSubmit}
          className="space-y-6"
        >
          <div>
            <label className="block text-sm font-medium text-soul-deep mb-1.5">角色名称 *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="例如：小艾"
              className="w-full px-4 py-2.5 rounded-xl border border-soul-sand bg-white text-soul-ink placeholder:text-soul-deep/50 focus:outline-none focus:ring-2 focus:ring-soul-rose/30"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-soul-deep mb-1.5">性别</label>
            <div className="flex gap-3">
              {GENDERS.map((g) => (
                <label
                  key={g.value}
                  className={clsx(
                    'flex items-center gap-2 px-4 py-2 rounded-xl border cursor-pointer transition-colors',
                    gender === g.value
                      ? 'border-soul-rose bg-soul-rose/10 text-soul-rose'
                      : 'border-soul-sand bg-white text-soul-deep/80 hover:border-soul-sage/50'
                  )}
                >
                  <input
                    type="radio"
                    name="gender"
                    value={g.value}
                    checked={gender === g.value}
                    onChange={() => setGender(g.value)}
                    className="sr-only"
                  />
                  {g.label}
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-soul-deep mb-1.5">头像（可选）</label>
            <div className="flex items-center gap-4">
              <div className="w-24 h-24 rounded-2xl bg-soul-sand/60 flex items-center justify-center overflow-hidden">
                {avatarPreview ? (
                  <img src={avatarPreview} alt="预览" className="w-full h-full object-cover" />
                ) : (
                  <span className="text-soul-deep/40 text-sm">未选</span>
                )}
              </div>
              <label className="px-4 py-2 rounded-xl border border-soul-sand bg-white text-soul-deep text-sm cursor-pointer hover:bg-soul-sand/30 transition-colors">
                选择图片
                <input type="file" accept="image/*" className="hidden" onChange={handleAvatarChange} />
              </label>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-soul-deep mb-1.5">背景与设定（系统提示词）*</label>
            <textarea
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              placeholder="详细描述角色的身份、背景、说话风格等，将作为 AI 的系统设定。"
              rows={5}
              className="w-full px-4 py-2.5 rounded-xl border border-soul-sand bg-white text-soul-ink placeholder:text-soul-deep/50 focus:outline-none focus:ring-2 focus:ring-soul-rose/30 resize-y"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-soul-deep mb-1.5">开场白（可选）</label>
            <textarea
              value={openingMessage}
              onChange={(e) => setOpeningMessage(e.target.value)}
              placeholder="例如：嗨，我是小艾，很高兴认识你。今天想聊点什么？"
              rows={3}
              className="w-full px-4 py-2.5 rounded-xl border border-soul-sand bg-white text-soul-ink placeholder:text-soul-deep/50 focus:outline-none focus:ring-2 focus:ring-soul-rose/30 resize-y"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-soul-deep mb-1.5">性格标签（逗号或空格分隔）</label>
            <input
              type="text"
              value={personality}
              onChange={(e) => setPersonality(e.target.value)}
              placeholder="温柔、体贴、幽默、知性"
              className="w-full px-4 py-2.5 rounded-xl border border-soul-sand bg-white text-soul-ink placeholder:text-soul-deep/50 focus:outline-none focus:ring-2 focus:ring-soul-rose/30"
            />
          </div>

          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={isPublic}
              onChange={(e) => setIsPublic(e.target.checked)}
              className="rounded border-soul-sand text-soul-rose focus:ring-soul-rose"
            />
            <span className="text-soul-deep">发布到角色广场，供他人使用</span>
          </label>

          {error && (
            <p className="text-red-600 text-sm">{error}</p>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full py-3 rounded-xl bg-soul-rose text-white font-medium hover:bg-soul-terracotta disabled:opacity-60 transition-colors"
          >
            {submitting ? '创建中…' : '创建并开始对话'}
          </button>
        </motion.form>
      </div>
    </div>
  );
}
