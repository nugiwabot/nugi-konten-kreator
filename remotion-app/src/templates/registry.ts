import catalog from '../../template-catalog.json';

export type LayoutName = 'landscape' | 'portrait' | 'square';
export type PresetName = 'cinematic' | 'documentary' | 'editorial' | 'minimal' | 'energetic';
export type TemplateDefinition = {
  id: string;
  compositionId: string;
  name: string;
  category: string;
  description: string;
  defaultDurationSeconds: number;
  presets: PresetName[];
  required: string[];
  optional: string[];
  defaultData: Record<string, unknown>;
};

type Catalog = {
  layouts: Record<LayoutName, {width: number; height: number}>;
  presets: PresetName[];
  animations: string[];
  templates: TemplateDefinition[];
};

export const TEMPLATE_CATALOG = catalog as Catalog;
export const TEMPLATE_REGISTRY = TEMPLATE_CATALOG.templates;
export const LAYOUTS = TEMPLATE_CATALOG.layouts;
export const PRESETS = TEMPLATE_CATALOG.presets;
export const ANIMATIONS = TEMPLATE_CATALOG.animations;

export const getTemplate = (id: string): TemplateDefinition | undefined =>
  TEMPLATE_REGISTRY.find((template) => template.id === id || template.compositionId === id);

export const isPreset = (value: string): value is PresetName =>
  PRESETS.includes(value as PresetName);

export const isLayout = (value: string): value is LayoutName =>
  value in LAYOUTS;

export const validateTemplateInput = (input: {
  templateId: string;
  preset?: string;
  layout?: string;
  animation?: string;
  data?: Record<string, unknown>;
}): string[] => {
  const issues: string[] = [];
  const template = getTemplate(input.templateId);
  if (!template) return [`Template tidak dikenal: ${input.templateId}`];
  if (input.preset && (!isPreset(input.preset) || !template.presets.includes(input.preset))) {
    issues.push(`Preset ${input.preset} tidak tersedia untuk ${template.id}.`);
  }
  if (input.layout && !isLayout(input.layout)) issues.push(`Layout tidak valid: ${input.layout}.`);
  if (input.animation && !ANIMATIONS.includes(input.animation)) issues.push(`Animation tidak dikenal: ${input.animation}.`);
  for (const key of template.required) {
    const value = input.data?.[key];
    if (value === undefined || value === null || value === '') issues.push(`Input wajib belum diisi: data.${key}.`);
  }
  return issues;
};
