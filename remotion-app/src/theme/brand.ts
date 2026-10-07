import tokens from '../../design-tokens.json';

export const brand = tokens.brand;
export const typography = tokens.typography;
export const spacing = tokens.spacing;
export const motionTokens = tokens.motion;

const motionProfile = (name: keyof typeof motionTokens.profiles) => motionTokens.profiles[name];

export const presetTokens = {
  cinematic: {background: brand.gradientDeep, foreground: brand.paper, accent: brand.gold, motion: 'slow-zoom', profile: motionProfile('cinematic'), line: 4, texture: 0.18},
  documentary: {background: brand.gradient, foreground: brand.ink, accent: brand.coral, motion: 'fade-up', profile: motionProfile('documentary'), line: 5, texture: 0.14},
  editorial: {background: brand.gradientPaper, foreground: brand.ink, accent: brand.orange, motion: 'slide-in', profile: motionProfile('editorial'), line: 6, texture: 0.04},
  minimal: {background: brand.paper, foreground: brand.ink, accent: brand.coral, motion: 'fade', profile: motionProfile('minimal'), line: 2, texture: 0},
  energetic: {background: brand.gradientSoft, foreground: brand.ink, accent: brand.coral, motion: 'wipe', profile: motionProfile('energetic'), line: 7, texture: 0.2},
} as const;

export type PresetName = keyof typeof presetTokens;
export type MotionProfile = typeof motionTokens.profiles[keyof typeof motionTokens.profiles];
