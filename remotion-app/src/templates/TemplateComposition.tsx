import React, {createContext, useContext} from 'react';
import {
  AbsoluteFill,
  Easing,
  Img,
  OffthreadVideo,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import type {CSSProperties} from 'react';
import {brand, motionTokens, presetTokens, spacing, typography} from '../theme/brand';
import type {MotionProfile} from '../theme/brand';
import {TEMPLATE_REGISTRY, getTemplate} from './registry';

export type TemplateProps = {
  templateId: string;
  preset?: string;
  layout?: string;
  animation?: string;
  durationSeconds?: number;
  durationInFrames?: number;
  fps?: number;
  data?: Record<string, unknown>;
};

export type MasterScene = {
  template: string;
  preset?: string;
  animation?: string;
  duration?: number;
  durationInFrames?: number;
  data?: Record<string, unknown>;
};

export type MasterProps = {
  video?: {width?: number; height?: number; fps?: number; layout?: string};
  scenes: MasterScene[];
};

const presets = presetTokens;
const MotionProfileContext = createContext<MotionProfile>(presets.documentary.profile);
const textValue = (data: Record<string, unknown>, key: string, fallback = ''): string => {
  const value = data[key];
  return value === undefined || value === null ? fallback : String(value);
};
const numberValue = (data: Record<string, unknown>, key: string, fallback: number): number => {
  const value = Number(data[key]);
  return Number.isFinite(value) ? value : fallback;
};
const itemsValue = (data: Record<string, unknown>, key: string): Record<string, unknown>[] => {
  const value = data[key];
  return Array.isArray(value) ? value.filter((item) => item && typeof item === 'object') as Record<string, unknown>[] : [];
};
const clamp01 = (value: number): number => Math.max(0, Math.min(1, Number.isFinite(value) ? value : 0));

const assetSource = (value: unknown): string | undefined => {
  if (typeof value !== 'string' || !value.trim()) return undefined;
  const source = value.trim();
  if (/^(https?:|data:|blob:|file:)/i.test(source)) return source;
  const clean = source.replace(/\\/g, '/').replace(/^\.?\/?public\//i, '').replace(/^\//, '');
  return staticFile(clean);
};

const enterStyle = (
  frame: number,
  duration: number,
  animation: string,
  delay = 0,
  index = 0,
  profile: MotionProfile = presets.documentary.profile,
  fps = 30,
  hierarchy: 'primary' | 'secondary' | 'tertiary' = 'primary',
): CSSProperties => {
  const safeDuration = Math.max(1, Number.isFinite(duration) ? duration : 1);
  const entrance = Math.max(1, Math.min(profile.entranceSeconds * fps, safeDuration * 0.45));
  const staggerFrames = Math.min(profile.staggerMs * fps / 1000, entrance * 0.24);
  const offset = Math.min(delay + index * staggerFrames, safeDuration * 0.24);
  const easingControl = motionTokens.easing[profile.easing as keyof typeof motionTokens.easing] as [number, number, number, number];
  const easing = Easing.bezier(...easingControl);
  const eased = (f: number) => interpolate(f, [offset, offset + entrance], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing,
  });
  const progress = clamp01(eased(frame));
  const exitDuration = Math.min(profile.exitSeconds * fps, safeDuration * 0.12);
  const exitStart = safeDuration - exitDuration;
  const hasExit = safeDuration >= fps * 2.5 && exitStart > offset + entrance + fps * 0.7;
  const exit = hasExit
    ? clamp01(interpolate(frame, [exitStart, safeDuration], [0, 1], {
      extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(...easingControl),
    }))
    : 0;
  const opacity = clamp01(progress * (1 - exit));
  const hierarchyScale = hierarchy === 'primary' ? 1 : hierarchy === 'secondary' ? 0.55 : 0.2;
  const distance = motionTokens.distance.medium * profile.travel * hierarchyScale * (1 - progress);
  const style: CSSProperties = {opacity};
  switch (animation) {
    case 'fade-down': style.transform = `translateY(${-distance}px)`; break;
    case 'fade-left': style.transform = `translateX(${distance}px)`; break;
    case 'fade-right': style.transform = `translateX(${-distance}px)`; break;
    case 'scale': case 'scale-reveal': style.transform = `scale(${1 - (1 - 0.97) * (1 - progress)})`; break;
    case 'slow-zoom': style.transform = `scale(${1 + (motionTokens.scale.subtle - 1) * clamp01(frame / safeDuration)})`; break;
    case 'horizontal-drift': style.transform = `translateX(${(0.5 - clamp01(frame / safeDuration)) * motionTokens.distance.small}px) scale(${motionTokens.scale.subtle})`; break;
    case 'vertical-drift': style.transform = `translateY(${(0.5 - clamp01(frame / safeDuration)) * motionTokens.distance.small}px) scale(${motionTokens.scale.subtle})`; break;
    case 'parallax': style.transform = `translateY(${(1 - progress) * distance - (frame / safeDuration) * motionTokens.distance.small * 0.35}px) scale(${motionTokens.scale.subtle})`; break;
    case 'slide': case 'slide-in': style.transform = `translateX(${(1 - progress) * distance}px)`; break;
    case 'counter': style.transform = `translateY(${distance * 0.4}px) scale(${1 - 0.02 * (1 - progress)})`; break;
    case 'mask-reveal': case 'clip-reveal': style.clipPath = `inset(0 ${100 - progress * 100}% 0 0)`; break;
    case 'wipe': style.clipPath = `inset(0 0 ${100 - progress * 100}% 0)`; break;
    case 'tracking-reveal': style.letterSpacing = `${0.18 * (1 - progress)}em`; break;
    case 'fade-up': case 'stagger': case 'word-stagger': case 'character-stagger': case 'line-stagger': style.transform = `translateY(${distance}px)`; break;
    case 'fade': default: break;
  }
  return style;
};

const Backdrop: React.FC<{background: string; texture: number}> = ({background, texture}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const drift = Math.sin(frame / Math.max(1, fps) * 0.34) * 7;
  return <AbsoluteFill style={{background, overflow: 'hidden'}}>
    <AbsoluteFill style={{background: `radial-gradient(ellipse at 15% 15%, ${brand.paperGlow} 0%, transparent 47%), radial-gradient(ellipse at 90% 92%, ${brand.deepGlow} 0%, transparent 48%)`, opacity: texture * 3}} />
    <svg viewBox="0 0 1920 1080" preserveAspectRatio="none" style={{position: 'absolute', inset: 0, width: '100%', height: '100%', opacity: texture * 2.3, transform: `translateX(${drift}px) scale(1.008)`}}>
      <path d="M-120 720 C 250 630 340 400 620 390 C 900 380 1090 660 1430 605 C 1650 570 1760 430 2050 400" fill="none" stroke={brand.paper} strokeWidth="56" strokeOpacity="0.32" />
      <path d="M-100 815 C 250 765 390 570 650 550 C 950 527 1100 755 1420 725 C 1705 699 1790 560 2040 525" fill="none" stroke={brand.gold} strokeWidth="14" strokeOpacity="0.52" />
      <path d="M-80 680 C 220 605 370 370 630 360 C 920 350 1100 630 1430 580 C 1690 540 1795 405 2040 378" fill="none" stroke={brand.paper} strokeWidth="5" strokeOpacity="0.74" />
    </svg>
  </AbsoluteFill>;
};

const Eyebrow: React.FC<{children?: React.ReactNode; color: string}> = ({children, color}) => children ? (
  <div style={{fontFamily: typography.family, fontSize: 'clamp(13px, 1.05vw, 22px)', fontWeight: typography.eyebrowWeight, letterSpacing: typography.trackingWide, color, textTransform: 'uppercase', lineHeight: 1.35}}>{children}</div>
) : null;

const AccentRule: React.FC<{color: string; width?: number; frame?: number; duration?: number; index?: number}> = ({color, width = 118, frame, duration, index = 0}) => {
  const profile = useContext(MotionProfileContext);
  const {fps} = useVideoConfig();
  const progress = frame === undefined || duration === undefined ? 1 : clamp01(Number(enterStyle(frame, duration, 'fade', 0, index, profile, fps, 'tertiary').opacity ?? 1));
  return <div style={{width, height: 5, marginTop: 25, borderRadius: 8, background: color, boxShadow: `0 5px 22px ${brand.shadow}`, transform: `scaleX(${progress})`, transformOrigin: 'left center', opacity: progress}} />;
};

const Copy: React.FC<{
  title?: string; subtitle?: string; eyebrow?: string; color: string; accent: string;
  width: number; align?: 'left' | 'center' | 'right'; animation: string; frame: number; duration: number;
  titleScale?: number; index?: number;
}> = ({title, subtitle, eyebrow, color, accent, width, align = 'left', animation, frame, duration, titleScale = 0.078, index = 0}) => {
  const profile = useContext(MotionProfileContext);
  const {fps} = useVideoConfig();
  const size = Math.min(width * titleScale, width * (title && title.length > 46 ? 0.059 : title && title.length > 30 ? 0.068 : titleScale));
  return (
    <div style={{display: 'flex', flexDirection: 'column', alignItems: align === 'center' ? 'center' : align === 'right' ? 'flex-end' : 'flex-start', textAlign: align, maxWidth: '100%', ...enterStyle(frame, duration, 'fade', 0, index, profile, fps)}}>
      {eyebrow ? <div style={enterStyle(frame, duration, 'fade', 0, 0, profile, fps, 'tertiary')}><Eyebrow color={accent}>{eyebrow}</Eyebrow></div> : null}
      {title ? <div style={{marginTop: eyebrow ? '0.7em' : 0, color, fontFamily: typography.family, fontSize: size, fontWeight: typography.displayWeight, lineHeight: 1.02, letterSpacing: animation === 'tracking-reveal' ? undefined : typography.tracking, maxWidth: '100%', overflowWrap: 'anywhere', textWrap: 'balance', ...enterStyle(frame, duration, animation, 0, 1, profile, fps, 'primary')}}>
        {animation === 'word-stagger' || animation === 'character-stagger' || animation === 'line-stagger'
          ? (animation === 'line-stagger' ? title.split('\n') : animation === 'character-stagger' ? Array.from(title) : title.match(/\S+\s*/g) ?? [title]).map((part, partIndex) => <span key={`${partIndex}-${part}`} style={{display: animation === 'line-stagger' ? 'block' : 'inline-block', whiteSpace: animation === 'line-stagger' ? 'normal' : 'pre', ...enterStyle(frame, duration, 'fade-up', 0, partIndex + 1, profile, fps, 'primary')}}>{part}</span>)
          : title}
      </div> : null}
      {subtitle ? <div style={{marginTop: '1.05em', color, opacity: 0.82, fontFamily: typography.family, fontSize: Math.max(22, width * 0.026), lineHeight: 1.38, fontWeight: typography.bodyWeight, maxWidth: '92%', overflowWrap: 'anywhere', ...enterStyle(frame, duration, 'fade-up', 0, 2, profile, fps, 'secondary')}}>{subtitle}</div> : null}
      {title ? <AccentRule color={accent} frame={frame} duration={duration} index={3} /> : null}
    </div>
  );
};

const FallbackVisual: React.FC<{label?: string; accent: string}> = ({label = 'MANUSIA · TEMPAT · PERUBAHAN', accent}) => (
  <AbsoluteFill style={{background: `linear-gradient(145deg, ${brand.gold}, ${brand.amber} 46%, ${brand.coral})`, display: 'flex', alignItems: 'flex-end', justifyContent: 'flex-start', padding: '7%'}}>
    <div style={{color: brand.ink, fontFamily: typography.family, fontSize: 'clamp(13px, 1.4vw, 26px)', fontWeight: 700, letterSpacing: typography.trackingWide, borderLeft: `3px solid ${accent}`, paddingLeft: 18}}>{label}</div>
  </AbsoluteFill>
);

const MediaPanel: React.FC<{
  image?: unknown; video?: unknown; label?: string; accent: string; position?: string; fit?: string; animation?: string;
  frame: number; duration: number; radius?: number;
}> = ({image, video, label, accent, position = 'center', fit = 'cover', animation = 'mask-reveal', frame, duration, radius = 20}) => {
  const profile = useContext(MotionProfileContext);
  const {fps} = useVideoConfig();
  const source = assetSource(video || image);
  const objectPosition = position === 'top' || position === 'bottom' || position === 'left' || position === 'right' ? position : 'center';
  const objectFit = fit === 'contain' ? 'contain' : 'cover';
  return (
    <div style={{position: 'relative', overflow: 'hidden', borderRadius: radius, background: brand.gradientSoft, boxShadow: `0 22px 54px ${brand.shadow}`, width: '100%', height: '100%', ...enterStyle(frame, duration, animation, 0, 0, profile, fps, 'secondary')}}>
      {source ? video ? <OffthreadVideo src={source} muted style={{width: '100%', height: '100%', objectFit, objectPosition}} /> : <Img src={source} style={{width: '100%', height: '100%', objectFit, objectPosition}} /> : <FallbackVisual label={label} accent={accent} />}
      <AbsoluteFill style={{background: `linear-gradient(0deg, ${brand.mediaShade}, transparent 54%)`}} />
    </div>
  );
};

const Page: React.FC<{children: React.ReactNode; inset?: number | string; style?: CSSProperties}> = ({children, inset = spacing.edge, style}) => (
  <AbsoluteFill style={{padding: typeof inset === 'number' ? `${inset * 100}%` : inset, display: 'flex', ...style}}>{children}</AbsoluteFill>
);

const TemplateScene: React.FC<TemplateProps> = ({templateId, preset = 'documentary', animation, data = {}, durationInFrames: sceneFrames}) => {
  const frame = useCurrentFrame();
  const {width, height, durationInFrames: compositionFrames, fps} = useVideoConfig();
  const template = getTemplate(templateId);
  const stylePreset = presets[preset as keyof typeof presets] ?? presets.documentary;
  const motion = animation ?? stylePreset.motion;
  const animate = (f: number, d: number, a: string, delay = 0, index = 0, hierarchy: 'primary' | 'secondary' | 'tertiary' = 'primary') => enterStyle(f, d, a, delay, index, stylePreset.profile, fps, hierarchy);
  const bg = textValue(data, 'background', stylePreset.background);
  const fg = textValue(data, 'foreground', stylePreset.foreground);
  const accent = textValue(data, 'accent', stylePreset.accent);
  const title = textValue(data, 'title');
  const subtitle = textValue(data, 'subtitle');
  const eyebrow = textValue(data, 'eyebrow');
  const duration = sceneFrames ?? compositionFrames;
  const portrait = height > width;
  const widePadding = portrait ? '9%' : '8.5%';
  const align = textValue(data, 'alignment', 'left') as 'left' | 'center' | 'right';
  const defaultLabel = textValue(data, 'imageLabel', 'Ruang hidup manusia');
  const source = textValue(data, 'source');
  const year = textValue(data, 'year');
  const titleProps = {title, subtitle, eyebrow, color: fg, accent, width, align, animation: animation ?? stylePreset.profile.titleMotion, frame, duration};

  if (!template) return <AbsoluteFill style={{background: bg, color: fg, padding: widePadding, justifyContent: 'center'}}><Copy {...titleProps} title="Template tidak ditemukan" /></AbsoluteFill>;

  let visual: React.ReactNode;
  switch (template.id) {
    case 'intro-bumper':
      visual = <Page inset={0.08} style={{alignItems: 'center', justifyContent: 'center', textAlign: 'center'}}><div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 22}}>
        {data.logo ? <Img src={assetSource(data.logo)!} style={{width: portrait ? '36vw' : '19vw', height: 'auto', objectFit: 'contain', ...animate(frame, duration, motion, 0, 0, 'primary')}} /> : <div style={{fontFamily: typography.family, color: fg, fontSize: portrait ? '17vw' : '11vw', fontWeight: 800, letterSpacing: '-0.07em', ...animate(frame, duration, motion, 0, 0, 'primary')}}>{title || 'NUGI'}</div>}
        <Eyebrow color={accent}>{eyebrow}</Eyebrow>
        <div style={{fontFamily: typography.family, fontSize: 'clamp(19px, 2vw, 38px)', color: fg, opacity: 0.9, maxWidth: '68vw', ...animate(frame, duration, 'fade-up', 0, 1, 'secondary')}}>{subtitle}</div>
      </div></Page>;
      break;
    case 'logo-reveal':
      visual = <Page inset={0.08} style={{alignItems: 'center', justifyContent: 'center'}}><div style={{textAlign: 'center', ...animate(frame, duration, 'mask-reveal')}}>
        {data.logo ? <Img src={assetSource(data.logo)!} style={{width: portrait ? '38vw' : '24vw', height: 'auto', objectFit: 'contain'}} /> : <div style={{fontFamily: typography.family, fontSize: portrait ? '18vw' : '12vw', lineHeight: 0.95, fontWeight: 800, color: fg, letterSpacing: '-0.08em'}}>{title || 'NUGI'}</div>}
        {subtitle ? <div style={{marginTop: 24, fontSize: 'clamp(16px, 1.7vw, 30px)', color: fg, letterSpacing: typography.trackingWide}}>{subtitle}</div> : null}
      </div></Page>;
      break;
    case 'minimal-intro':
      visual = <Page inset={widePadding} style={{alignItems: 'center', justifyContent: 'center'}}><Copy {...titleProps} titleScale={portrait ? 0.095 : 0.082} /></Page>;
      break;
    case 'title-card':
      visual = <Page inset={widePadding} style={{alignItems: 'center', justifyContent: 'center', flexDirection: portrait ? 'column' : 'row', gap: '6%'}}>
        {data.image ? <div style={{width: portrait ? '100%' : '43%', height: portrait ? '42%' : '76%'}}><MediaPanel image={data.image} label={defaultLabel} accent={accent} position={textValue(data, 'position', 'center')} fit={textValue(data, 'fit', 'cover')} frame={frame} duration={duration} /></div> : null}
        <div style={{width: data.image ? (portrait ? '100%' : '51%') : '100%'}}><Copy {...titleProps} titleScale={portrait ? 0.09 : 0.078} /></div>
      </Page>;
      break;
    case 'chapter-title': {
      const chapter = textValue(data, 'chapter', '01');
      visual = <Page inset={widePadding} style={{alignItems: 'center', justifyContent: 'center', flexDirection: portrait ? 'column' : 'row', gap: '4%'}}>
        <div style={{color: accent, opacity: 0.66, fontSize: portrait ? '34vw' : '25vw', fontFamily: typography.family, fontWeight: 760, lineHeight: 0.78, letterSpacing: '-0.09em', ...animate(frame, duration, 'fade-up', 0, 0, 'secondary')}}>{chapter}</div>
        <div style={{maxWidth: portrait ? '100%' : '62%'}}><Copy {...titleProps} titleScale={0.075} /></div>
      </Page>;
      break;
    }
    case 'documentary-text':
      visual = <Page inset={0} style={{alignItems: 'center', justifyContent: 'center'}}>
        {data.image || data.video ? <MediaPanel image={data.image} video={data.video} label={defaultLabel} accent={accent} position={textValue(data, 'position', 'center')} fit={textValue(data, 'fit', 'cover')} frame={frame} duration={duration} animation="slow-zoom" radius={0} /> : null}
        <AbsoluteFill style={{background: data.image || data.video ? `linear-gradient(90deg, ${brand.documentaryShade}, ${brand.documentaryShadeEnd})` : 'transparent'}} />
        <div style={{position: 'relative', zIndex: 1, padding: widePadding, width: '100%'}}><Copy {...titleProps} color={data.image || data.video ? brand.paper : fg} titleScale={0.085} /></div>
      </Page>;
      break;
    case 'headline':
      visual = <Page inset={widePadding} style={{justifyContent: 'space-between'}}>
        <div style={{display: 'flex', alignItems: 'center', gap: 20}}><div style={{width: 14, height: 14, borderRadius: '50%', background: accent}} /><Eyebrow color={accent}>{eyebrow || 'NUGI · EDITORIAL'}</Eyebrow><div style={{height: 1, flex: 1, background: `${fg}45`}} /></div>
        <div style={{maxWidth: portrait ? '100%' : '85%', marginTop: 'auto'}}><Copy {...titleProps} titleScale={portrait ? 0.093 : 0.079} /><div style={{marginTop: 26, color: fg, opacity: 0.68, fontSize: 'clamp(14px, 1.2vw, 22px)'}}>{source}</div></div>
      </Page>;
      break;
    case 'statistic':
    case 'number-counter': {
      const value = data.number ?? '68%';
      const numeric = Number(String(value).replace(/[^\d.-]/g, ''));
      const isCounter = template.id === 'number-counter' && Number.isFinite(numeric);
      const counterEase = motionTokens.easing[stylePreset.profile.easing as keyof typeof motionTokens.easing] as [number, number, number, number];
      const countProgress = clamp01(interpolate(frame, [0, Math.max(1, Math.min(stylePreset.profile.entranceSeconds * fps, duration * 0.45))], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(...counterEase)}));
      const displayNumber = isCounter ? `${Math.round(numeric * countProgress)}${textValue(data, 'unit', String(value).match(/[^\d.-]+$/)?.[0] ?? '')}` : String(value);
      visual = <Page inset={widePadding} style={{justifyContent: 'center', flexDirection: portrait ? 'column' : 'row', alignItems: 'center', gap: '7%'}}>
        <div style={{fontFamily: typography.family, color: accent, fontWeight: 780, fontSize: portrait ? '27vw' : '22vw', lineHeight: 0.86, letterSpacing: '-0.08em', ...animate(frame, duration, isCounter ? 'counter' : motion, 0, 0, 'primary')}}>{displayNumber}</div>
        <div style={{maxWidth: portrait ? '100%' : '43%', display: 'flex', flexDirection: 'column', gap: 20, ...animate(frame, duration, motion, 0, 1, 'secondary')}}>
          <Eyebrow color={accent}>{template.id === 'statistic' ? 'ANGKA YANG BERCERITA' : 'SEBUAH PERUBAHAN'}</Eyebrow>
          <div style={{fontFamily: typography.family, color: fg, fontSize: portrait ? '7.5vw' : '4vw', fontWeight: 730, lineHeight: 1.08, textWrap: 'balance'}}>{textValue(data, 'label')}</div>
          {subtitle || textValue(data, 'description') ? <div style={{fontSize: portrait ? '4vw' : '1.8vw', lineHeight: 1.4, color: fg, opacity: 0.78}}>{textValue(data, 'description', subtitle)}</div> : null}
          {source || year ? <div style={{fontSize: 'clamp(14px, 1vw, 20px)', color: fg, opacity: 0.68, letterSpacing: '0.03em'}}>{[source, year].filter(Boolean).join(' · ')}</div> : null}
        </div>
      </Page>;
      break;
    }
    case 'fact-card':
      visual = <Page inset={widePadding} style={{alignItems: 'center', justifyContent: 'center'}}><div style={{width: '100%', maxWidth: '1200px', padding: portrait ? '9%' : '6%', background: brand.surfaceLight, border: `1px solid ${brand.border}`, borderRadius: 28, boxShadow: `0 24px 64px ${brand.shadow}`, ...animate(frame, duration, motion)}}>
        <Eyebrow color={accent}>{eyebrow || 'FAKTA YANG MENGUBAH CERITA'}</Eyebrow><div style={{fontFamily: typography.family, fontSize: portrait ? '7.4vw' : '5.2vw', color: fg, fontWeight: 740, lineHeight: 1.08, marginTop: 24, textWrap: 'balance'}}>{title}</div>
        {subtitle || textValue(data, 'description') ? <div style={{fontSize: portrait ? '3.8vw' : '1.8vw', lineHeight: 1.45, color: fg, opacity: 0.78, marginTop: 30}}>{textValue(data, 'description', subtitle)}</div> : null}
        {source ? <div style={{marginTop: 42, fontSize: 'clamp(13px, 1vw, 20px)', color: accent, letterSpacing: typography.trackingWide}}>{source}{year ? ` · ${year}` : ''}</div> : null}
      </div></Page>;
      break;
    case 'quote-card':
      visual = <Page inset={widePadding} style={{alignItems: 'center', justifyContent: 'center'}}><div style={{maxWidth: '82%', textAlign: 'center', ...animate(frame, duration, 'fade')}}>
        <div style={{fontFamily: typography.quoteFamily, fontSize: portrait ? '26vw' : '18vw', lineHeight: 0.55, color: accent, opacity: 0.82}}>“</div>
        <div style={{fontFamily: typography.family, color: fg, fontSize: portrait ? '7.6vw' : '5vw', fontWeight: 620, lineHeight: 1.14, letterSpacing: '-0.025em', textWrap: 'balance'}}>{textValue(data, 'quote', title)}</div>
        <AccentRule color={accent} frame={frame} duration={duration} index={3} /><div style={{marginTop: 30, color: fg, fontSize: 'clamp(18px, 1.65vw, 32px)', fontWeight: 700, ...animate(frame, duration, 'fade', 0, 2, 'tertiary')}}>{textValue(data, 'author')}</div><div style={{marginTop: 8, color: fg, opacity: 0.65, fontSize: 'clamp(14px, 1.1vw, 22px)', ...animate(frame, duration, 'fade', 0, 3, 'tertiary')}}>{source}</div>
      </div></Page>;
      break;
    case 'timeline': {
      const events = itemsValue(data, 'events');
      const vertical = textValue(data, 'orientation', portrait ? 'vertical' : 'horizontal') === 'vertical' || portrait;
      visual = <Page inset={widePadding} style={{justifyContent: 'center'}}><div style={{width: '100%'}}>
        {title ? <div style={{fontFamily: typography.family, color: fg, fontSize: portrait ? '7vw' : '4.1vw', fontWeight: 740, lineHeight: 1.08, marginBottom: '6%', ...animate(frame, duration, stylePreset.profile.titleMotion, 0, 0, 'primary')}}>{title}</div> : null}
        <div style={{display: 'flex', flexDirection: vertical ? 'column' : 'row', alignItems: vertical ? 'stretch' : 'flex-start', gap: vertical ? 24 : '3%', position: 'relative'}}>
          {!vertical ? <div style={{position: 'absolute', left: 0, right: 0, top: 14, height: 2, background: `${accent}90`}} /> : null}
          {events.slice(0, 5).map((event, i) => <div key={`${event.year}-${i}`} style={{position: 'relative', flex: 1, display: 'flex', flexDirection: vertical ? 'row' : 'column', gap: vertical ? 22 : 18, ...animate(frame, duration, 'fade-up', 0, i, 'secondary')}}>
            <div style={{width: 28, height: 28, borderRadius: '50%', background: accent, border: `6px solid ${brand.paper}`, boxShadow: `0 0 0 2px ${accent}`, flex: '0 0 auto', zIndex: 1}} />
            <div><div style={{fontSize: 'clamp(15px, 1.3vw, 26px)', fontWeight: 780, color: accent, letterSpacing: '0.02em'}}>{textValue(event, 'year')}</div><div style={{fontSize: portrait ? '4vw' : '2vw', fontWeight: 740, color: fg, marginTop: 10, lineHeight: 1.1}}>{textValue(event, 'title')}</div><div style={{fontSize: portrait ? '3.2vw' : '1.3vw', lineHeight: 1.35, color: fg, opacity: 0.72, marginTop: 10}}>{textValue(event, 'detail')}</div></div>
          </div>)}
        </div>
      </div></Page>;
      break;
    }
    case 'image-reveal':
      visual = <Page inset={widePadding} style={{alignItems: 'center', justifyContent: 'center', flexDirection: portrait ? 'column' : 'row', gap: '6%'}}>
        <div style={{width: portrait ? '100%' : '52%', height: portrait ? '43%' : '72%'}}><MediaPanel image={data.image} video={data.video} label={defaultLabel} accent={accent} position={textValue(data, 'position', 'center')} fit={textValue(data, 'fit', 'cover')} animation="mask-reveal" frame={frame} duration={duration} /></div>
        <div style={{width: portrait ? '100%' : '42%'}}><Copy {...titleProps} titleScale={0.069} /></div>
      </Page>;
      break;
    case 'image-focus':
      visual = <Page inset={0} style={{justifyContent: 'flex-end'}}>
        <MediaPanel image={data.image} video={data.video} label={defaultLabel} accent={accent} position={textValue(data, 'position', 'center')} fit={textValue(data, 'fit', 'cover')} animation="slow-zoom" frame={frame} duration={duration} radius={0} />
        <AbsoluteFill style={{background: `linear-gradient(0deg, ${brand.focusShade}, ${brand.focusShadeEnd} 77%)`}} />
        <div style={{position: 'relative', zIndex: 1, padding: widePadding, width: '100%'}}><Copy {...titleProps} color={brand.paper} titleScale={0.069} /></div>
      </Page>;
      break;
    case 'photo-sequence': {
      const images = Array.isArray(data.images) ? data.images : [];
      const frameIndex = images.length ? Math.min(images.length - 1, Math.floor((frame / Math.max(1, duration)) * images.length)) : 0;
      const imageValue = images[frameIndex];
      const imagePath = typeof imageValue === 'string' ? imageValue : imageValue && typeof imageValue === 'object' ? String((imageValue as Record<string, unknown>).image ?? '') : '';
      const captionData = Array.isArray(data.captions) ? data.captions : [];
      const captionValue = typeof imageValue === 'object' && imageValue ? String((imageValue as Record<string, unknown>).caption ?? '') : String(captionData[frameIndex] ?? '');
      visual = <Page inset={portrait ? 0.07 : 0.06} style={{justifyContent: 'center'}}><div style={{width: '100%', height: '100%', position: 'relative'}}>
        <MediaPanel image={imagePath || data.image} label={defaultLabel} accent={accent} position={textValue(data, 'position', 'center')} fit={textValue(data, 'fit', 'cover')} animation="fade" frame={frame} duration={duration} radius={24} />
        <AbsoluteFill style={{background: `linear-gradient(0deg, ${brand.sequenceShade}, transparent 64%)`}} />
        <div style={{position: 'absolute', left: '7%', right: '7%', bottom: '8%', zIndex: 1}}><Eyebrow color={brand.gold}>{title}</Eyebrow><div style={{marginTop: 12, color: brand.paper, fontSize: portrait ? '5vw' : '2.7vw', fontWeight: 700}}>{captionValue}</div></div>
      </div></Page>;
      break;
    }
    case 'split-screen': {
      const imageFirst = textValue(data, 'position', 'left') !== 'right';
      const media = <div style={{width: portrait ? '100%' : '48%', height: portrait ? '48%' : '100%'}}><MediaPanel image={data.image} video={data.video} label={defaultLabel} accent={accent} position={textValue(data, 'mediaPosition', 'center')} fit={textValue(data, 'fit', 'cover')} frame={frame} duration={duration} /></div>;
      const copy = <div style={{width: portrait ? '100%' : '46%', display: 'flex', alignItems: 'center'}}><Copy {...titleProps} titleScale={0.068} /></div>;
      visual = <Page inset={widePadding} style={{flexDirection: portrait ? 'column' : 'row', alignItems: 'center', justifyContent: 'space-between', gap: '4%'}}>{imageFirst ? <>{media}{copy}</> : <>{copy}{media}</>}</Page>;
      break;
    }
    case 'lower-third':
      visual = (
        <Page inset={widePadding} style={{justifyContent: 'flex-end', alignItems: textValue(data, 'position', 'left') === 'right' ? 'flex-end' : 'flex-start'}}>
          <div style={{display: 'flex', alignItems: 'stretch', gap: 22, borderRadius: 12, padding: '20px 28px', background: brand.surface, border: `1px solid ${brand.border}`, maxWidth: '86%', ...animate(frame, duration, 'slide-in', 0, 0, 'secondary')}}>
            <div style={{width: 6, background: accent, borderRadius: 4}} />
            <div>
              <div style={{fontFamily: typography.family, color: fg, fontSize: 'clamp(22px, 2.5vw, 48px)', fontWeight: 760}}>{title}</div>
              <div style={{marginTop: 5, color: fg, opacity: 0.76, fontSize: 'clamp(15px, 1.3vw, 25px)'}}>{subtitle || source}</div>
            </div>
          </div>
        </Page>
      );
      break;
    case 'before-after': {
      const before = <div style={{flex: 1, position: 'relative', minHeight: portrait ? '34%' : '72%'}}><MediaPanel image={data.imageBefore} label={textValue(data, 'beforeText', defaultLabel)} accent={accent} position={textValue(data, 'beforePosition', 'center')} fit={textValue(data, 'fit', 'cover')} animation="fade-left" frame={frame} duration={duration} radius={18} /><div style={{position: 'absolute', top: 18, left: 18, zIndex: 1, color: brand.ink, background: brand.gold, padding: '9px 15px', borderRadius: 5, fontWeight: 800, letterSpacing: typography.trackingWide}}>{textValue(data, 'beforeLabel', 'DAHULU')}</div></div>;
      const after = <div style={{flex: 1, position: 'relative', minHeight: portrait ? '34%' : '72%'}}><MediaPanel image={data.imageAfter} label={textValue(data, 'afterText', defaultLabel)} accent={accent} position={textValue(data, 'afterPosition', 'center')} fit={textValue(data, 'fit', 'cover')} animation="fade-right" frame={frame} duration={duration} radius={18} /><div style={{position: 'absolute', top: 18, left: 18, zIndex: 1, color: brand.paper, background: brand.coral, padding: '9px 15px', borderRadius: 5, fontWeight: 800, letterSpacing: typography.trackingWide}}>{textValue(data, 'afterLabel', 'SEKARANG')}</div></div>;
      visual = <Page inset={widePadding} style={{flexDirection: 'column', justifyContent: 'center', gap: 22}}>{title ? <Eyebrow color={accent}>{title}</Eyebrow> : null}<div style={{display: 'flex', flexDirection: portrait ? 'column' : 'row', gap: 20, flex: 1, minHeight: 0}}>{before}{after}</div></Page>;
      break;
    }
    case 'progress-bar': {
      const total = Math.max(1, numberValue(data, 'total', 6));
      const progress = clamp01(numberValue(data, 'progress', numberValue(data, 'chapter', 1) / total));
      visual = <Page inset={widePadding} style={{justifyContent: 'flex-end'}}><div style={{width: '100%', ...animate(frame, duration, 'fade')}}>
        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', color: fg, marginBottom: 22}}><Eyebrow color={accent}>BAB {textValue(data, 'chapter', '1')} / {total}</Eyebrow><div style={{fontSize: 'clamp(14px, 1vw, 20px)', opacity: 0.72}}>NUGI · HUMAN × PLACE</div></div>
        <div style={{fontFamily: typography.family, fontSize: portrait ? '8vw' : '5vw', lineHeight: 1.05, fontWeight: 760, color: fg, maxWidth: '80%'}}>{title}</div>
        {subtitle ? <div style={{marginTop: 15, color: fg, opacity: 0.74, fontSize: 'clamp(18px, 1.6vw, 30px)'}}>{subtitle}</div> : null}
        <div style={{width: '100%', height: 5, background: brand.track, marginTop: 44, overflow: 'hidden', borderRadius: 8}}><div style={{width: `${progress * 100}%`, height: '100%', background: accent}} /></div>
      </div></Page>;
      break;
    }
    case 'outro':
      visual = <Page inset={0.08} style={{alignItems: 'center', justifyContent: 'center', textAlign: 'center'}}><div style={{maxWidth: '78%', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 18, ...animate(frame, duration, 'fade')}}>
        <div style={animate(frame, duration, 'fade', 0, 0, 'tertiary')}><Eyebrow color={accent}>NUGI · HUMAN × PLACE × WHY</Eyebrow></div><div style={{fontFamily: typography.family, color: fg, fontSize: portrait ? '8vw' : '5vw', fontWeight: 760, lineHeight: 1.06, textWrap: 'balance', ...animate(frame, duration, stylePreset.profile.titleMotion, 0, 1, 'primary')}}>{title}</div><div style={{fontSize: portrait ? '4vw' : '1.8vw', color: fg, opacity: 0.78, lineHeight: 1.4, ...animate(frame, duration, 'fade-up', 0, 2, 'secondary')}}>{subtitle}</div><AccentRule color={accent} frame={frame} duration={duration} index={3} /><div style={{fontSize: 'clamp(16px, 1.3vw, 24px)', color: fg, opacity: 0.82, marginTop: 12, ...animate(frame, duration, 'fade', 0, 4, 'tertiary')}}>{textValue(data, 'cta')}</div>
      </div></Page>;
      break;
    default:
      visual = <Page inset={widePadding} style={{alignItems: 'center', justifyContent: 'center'}}><Copy {...titleProps} title={title || template.name} /></Page>;
  }

  return <MotionProfileContext.Provider value={stylePreset.profile}><AbsoluteFill style={{fontFamily: typography.family, overflow: 'hidden'}}><Backdrop background={bg} texture={stylePreset.texture} />{visual}</AbsoluteFill></MotionProfileContext.Provider>;
};

export const TemplateComposition: React.FC<TemplateProps> = (props) => <TemplateScene {...props} />;

export const MasterSequence: React.FC<MasterProps> = ({video, scenes = []}) => {
  let cursor = 0;
  const sequenceElements = scenes.map((scene, index) => {
    const template = getTemplate(scene.template);
    if (!template) throw new Error(`Unknown scene template: ${scene.template}`);
    const frames = Math.max(1, Math.round(Number(scene.durationInFrames ?? scene.duration ?? template.defaultDurationSeconds * (video?.fps ?? 30))));
    const start = cursor;
    cursor += frames;
    return <Sequence key={`${template.id}-${index}`} from={start} durationInFrames={frames} name={template.name}>
      <TemplateScene templateId={template.id} preset={scene.preset ?? 'documentary'} animation={scene.animation} data={scene.data ?? template.defaultData} durationInFrames={frames} />
    </Sequence>;
  });
  return <AbsoluteFill>{sequenceElements}</AbsoluteFill>;
};

export const TemplateGallery: React.FC = () => {
  const {width, fps} = useVideoConfig();
  const columns = 4;
  const cellWidth = width / columns;
  const cellHeight = 216;
  return <AbsoluteFill style={{background: brand.ink, display: 'grid', gridTemplateColumns: `repeat(${columns}, 1fr)`, gridTemplateRows: 'repeat(5, 1fr)'}}>
    {TEMPLATE_REGISTRY.map((template, index) => <div key={template.id} style={{position: 'relative', overflow: 'hidden', width: cellWidth, height: cellHeight, border: `1px solid ${brand.border}`}}>
      <div style={{position: 'absolute', width: 1920, height: 1080, left: (cellWidth - 384) / 2, top: -27, transform: 'scale(0.2)', transformOrigin: 'top left'}}>
        <TemplateScene templateId={template.id} preset={template.presets.includes('documentary') ? 'documentary' : template.presets[0]} data={template.defaultData} durationInFrames={template.defaultDurationSeconds * fps} />
      </div>
      <div style={{position: 'absolute', zIndex: 10, left: 0, right: 0, bottom: 0, height: 37, background: brand.galleryShade, color: brand.paper, display: 'flex', alignItems: 'center', padding: '0 13px', fontFamily: typography.family, fontSize: 15, letterSpacing: '0.04em'}}>{String(index + 1).padStart(2, '0')} · {template.name}</div>
    </div>)}
  </AbsoluteFill>;
};

export const canvasForLayout = (layout: string): {width: number; height: number} => {
  if (layout === 'portrait') return {width: 1080, height: 1920};
  if (layout === 'square') return {width: 1080, height: 1080};
  return {width: 1920, height: 1080};
};

export const masterDurationInFrames = (props: MasterProps): number =>
  Math.max(1, (props.scenes ?? []).reduce((sum, scene) => {
    const template = getTemplate(scene.template);
    const fps = props.video?.fps ?? 30;
    return sum + Math.max(1, Math.round(Number(scene.durationInFrames ?? scene.duration ?? (template?.defaultDurationSeconds ?? 5) * fps)));
  }, 0));

export const galleryTemplateCount = TEMPLATE_REGISTRY.length;
