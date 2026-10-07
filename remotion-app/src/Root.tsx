import React from 'react';
import {Composition} from 'remotion';
import {TitleCard, type TitleCardProps} from './TitleCard';
import {brand} from './theme/brand';
import {TEMPLATE_REGISTRY, type LayoutName} from './templates/registry';
import {
  MasterSequence,
  TemplateComposition,
  TemplateGallery,
  canvasForLayout,
  masterDurationInFrames,
  type MasterProps,
  type TemplateProps,
} from './templates/TemplateComposition';

const titleCardDefaults: TitleCardProps = {
  title: 'Kenapa Manusia Membutuhkan Rumah?',
  subtitle: 'Dari gua sampai megacity',
  background: brand.gradient,
  textAlignment: 'left',
};

const masterDefaults: MasterProps = {
  video: {width: 1920, height: 1080, fps: 30},
  scenes: [
    {template: 'intro-bumper', duration: 120, preset: 'cinematic', data: TEMPLATE_REGISTRY[0].defaultData},
    {template: 'title-card', duration: 180, preset: 'documentary', data: TEMPLATE_REGISTRY.find((item) => item.id === 'title-card')!.defaultData},
    {template: 'statistic', duration: 150, preset: 'editorial', data: TEMPLATE_REGISTRY.find((item) => item.id === 'statistic')!.defaultData},
  ],
};

export const RemotionRoot: React.FC = () => (
  <>
    {/* Backward-compatible composition used by existing video-mcp callers. */}
    <Composition
      id="TitleCard"
      component={TitleCard}
      durationInFrames={180}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={titleCardDefaults}
    />

    {TEMPLATE_REGISTRY.map((template) => {
      const defaultProps: TemplateProps = {
        templateId: template.id,
        preset: template.presets.includes('documentary') ? 'documentary' : template.presets[0],
        layout: 'landscape',
        durationSeconds: template.defaultDurationSeconds,
        data: template.defaultData,
      };
      return (
        <Composition
          key={template.compositionId}
          id={template.compositionId}
          component={TemplateComposition}
          durationInFrames={Math.max(1, Math.round(template.defaultDurationSeconds * 30))}
          fps={30}
          width={1920}
          height={1080}
          defaultProps={defaultProps}
          calculateMetadata={({props}) => {
            const layout = (props.layout || 'landscape') as LayoutName;
            const canvas = canvasForLayout(layout);
            const fps = Number.isFinite(Number(props.fps)) && Number(props.fps) > 0 ? Number(props.fps) : 30;
            const seconds = Number.isFinite(Number(props.durationSeconds)) && Number(props.durationSeconds) > 0
              ? Number(props.durationSeconds)
              : template.defaultDurationSeconds;
            return {width: canvas.width, height: canvas.height, fps, durationInFrames: Math.max(1, Math.round(seconds * fps))};
          }}
        />
      );
    })}

    <Composition
      id="Nugi-MasterSequence"
      component={MasterSequence}
      durationInFrames={450}
      fps={30}
      width={1920}
      height={1080}
      defaultProps={masterDefaults}
      calculateMetadata={({props}) => {
        const video = props.video ?? {};
        const layout = canvasForLayout(video.layout ?? 'landscape');
        const fps = Number.isFinite(Number(video.fps)) && Number(video.fps) > 0 ? Number(video.fps) : 30;
        return {
          width: Math.max(1, Number(video.width) || layout.width),
          height: Math.max(1, Number(video.height) || layout.height),
          fps,
          durationInFrames: masterDurationInFrames({...props, video: {...video, fps}}),
        };
      }}
    />

    <Composition
      id="Nugi-TemplateGallery"
      component={TemplateGallery}
      durationInFrames={60}
      fps={30}
      width={1920}
      height={1080}
    />
  </>
);
