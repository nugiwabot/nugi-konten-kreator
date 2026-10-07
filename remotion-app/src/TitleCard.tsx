import React from 'react';
import {AbsoluteFill} from 'remotion';
import {brand, typography} from './theme/brand';

export type TitleCardProps = {
  title: string;
  subtitle: string;
  background?: string;
  textAlignment: 'left' | 'center' | 'right';
};

export const TitleCard: React.FC<TitleCardProps> = ({
  title,
  subtitle,
  background = brand.gradient,
  textAlignment,
}) => {
  const justifyContent =
    textAlignment === 'left'
      ? 'flex-start'
      : textAlignment === 'right'
        ? 'flex-end'
        : 'center';
  const alignItems =
    textAlignment === 'left'
      ? 'flex-start'
      : textAlignment === 'right'
        ? 'flex-end'
        : 'center';

  return (
    <AbsoluteFill
      style={{
        background,
        color: brand.ink,
        display: 'flex',
        flexDirection: 'column',
        alignItems,
        justifyContent: 'center',
        padding: '10%',
        textAlign: textAlignment,
        fontFamily: typography.family,
      }}
    >
      <div style={{width: '100%', display: 'flex', flexDirection: 'column', alignItems}}>
        <div
          style={{
            alignSelf: justifyContent,
            fontSize: '8cqw',
            fontWeight: 800,
            lineHeight: 1.08,
            letterSpacing: '-0.035em',
            maxWidth: '100%',
            overflowWrap: 'anywhere',
          }}
        >
          {title}
        </div>
        {subtitle ? (
          <div
            style={{
              alignSelf: justifyContent,
              marginTop: '3cqh',
            color: brand.mutedInk,
              fontSize: '3.2cqw',
              lineHeight: 1.35,
              maxWidth: '90%',
            }}
          >
            {subtitle}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
