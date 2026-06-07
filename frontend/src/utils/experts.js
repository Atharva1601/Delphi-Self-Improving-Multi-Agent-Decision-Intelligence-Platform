/**
 * src/utils/experts.js
 * Maps expert names → icon emoji and domain color.
 */

export const EXPERT_MAP = {
  'Finance Expert': {
    icon: '💰',
    color: '#34D399',
    label: 'Finance',
  },
  'Legal Expert': {
    icon: '⚖️',
    color: '#6C63FF',
    label: 'Legal',
  },
  'Security Expert': {
    icon: '🛡️',
    color: '#F87171',
    label: 'Security',
  },
  'Technical Architect Expert': {
    icon: '🏗️',
    color: '#60A5FA',
    label: 'Architecture',
  },
  'Operations Expert': {
    icon: '⚙️',
    color: '#FBBF24',
    label: 'Operations',
  },
  'Product Strategy Expert': {
    icon: '🎯',
    color: '#F472B6',
    label: 'Strategy',
  },
  'Business / Market Expert': {
    icon: '📈',
    color: '#F5C842',
    label: 'Business',
  },
};

/** Returns icon/color/label for any expert name (fuzzy match). */
export function getExpertMeta(name = '') {
  if (!name) return { icon: '🧠', color: '#6C63FF', label: 'Expert' };

  // Exact match first
  if (EXPERT_MAP[name]) return EXPERT_MAP[name];

  // Fuzzy: find a key that the name includes or vice versa
  const lower = name.toLowerCase();
  for (const [key, val] of Object.entries(EXPERT_MAP)) {
    if (lower.includes(key.toLowerCase().split(' ')[0])) return val;
  }

  return { icon: '🧠', color: '#6C63FF', label: name };
}
