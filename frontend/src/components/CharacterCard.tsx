import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Trash2 } from 'lucide-react';
import type { Character } from '@/types';

interface CharacterCardProps {
  character: Character;
  index?: number;
  canDelete?: boolean;
  deleting?: boolean;
  onRequestDelete?: (character: Character) => void;
}

export function CharacterCard({
  character,
  index = 0,
  canDelete = false,
  deleting = false,
  onRequestDelete,
}: CharacterCardProps) {
  return (
    <motion.article
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.35 }}
      className="group relative"
    >
      {canDelete && (
        <button
          type="button"
          disabled={deleting}
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onRequestDelete?.(character);
          }}
          className="absolute right-2 top-2 z-20 p-2 rounded-full bg-white/90 border border-soul-sand text-red-500 hover:bg-red-50 disabled:opacity-60"
          title={deleting ? '删除中…' : '删除角色'}
        >
          <Trash2 className="w-4 h-4" />
        </button>
      )}
      <Link
        to={`/chat/${character.id}`}
        className="block rounded-2xl overflow-hidden bg-white/80 border border-soul-sand/60 shadow-sm hover:shadow-lg hover:border-soul-sage/50 transition-all duration-300"
      >
        <div className="aspect-[4/5] relative bg-gradient-soft overflow-hidden">
          {character.avatar_url ? (
            <img
              src={character.avatar_url}
              alt={character.name}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-soul-sage/60 text-4xl font-display">
              {character.name.charAt(0)}
            </div>
          )}
          <div className="absolute inset-0 bg-gradient-to-t from-soul-ink/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>
        <div className="p-4">
          <h3 className="font-display text-lg font-semibold text-soul-ink truncate">{character.name}</h3>
          <p className="text-xs text-soul-deep/60 mt-0.5">
            {character.gender === 'female' ? '她' : character.gender === 'male' ? '他' : 'TA'}
            {character.personality?.length ? ` · ${character.personality.slice(0, 2).join('、')}` : ''}
          </p>
          {character.creator_name && (
            <p className="text-xs text-soul-sage mt-1">by {character.creator_name}</p>
          )}
        </div>
      </Link>
    </motion.article>
  );
}
