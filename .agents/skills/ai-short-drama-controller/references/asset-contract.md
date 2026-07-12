# Asset contract / 资产生成契约

## General / 通用规则

Every prompt must be complete, standalone, and directly usable by an image model.

每个提示词必须独立包含：画面风格、主体、外观、材质、色彩、构图、背景、光线、画幅、禁止项。不得依赖“沿用上一条”“同上”或隐藏母版。

Use stable IDs:

- `C01-C99` characters / 人物
- `S01-S99` scenes / 场景
- `P01-P99` props / 道具

## Character sheet / 人物资产图

Default format unless the user explicitly specifies otherwise:

- horizontal `16:9 横向`
- pure white background / 纯白背景
- left 35%: front head-and-shoulders close-up / 左侧35%正面大头照
- right 65%: full-body front, right profile, and back views / 右侧65%正面、右侧面、背面三视图
- bottom 13%: thin detail strip / 下方13%薄细节带
- whole body visible, no cropping / 全身完整，不裁脚、不裁头

Detail strip should show only production-relevant details, such as:

- face and eye details
- hairstyle and hair accessory
- costume fabric, seam, fastener, armor, or embroidery
- footwear
- signature prop or weapon
- compact color swatches when requested

Identity locks:

- same face
- same apparent age
- same body proportion
- same hairstyle
- same costume construction
- same costume materials and colors
- same signature marks
- same weapon dimensions and materials

Do not turn the sheet into a poster, illustration layout, cinematic key art, or interface mockup.

## Scene asset / 场景资产

A scene asset shows the reusable physical environment, not a finished dramatic shot.

Required:

- empty scene unless scale figures are explicitly requested
- fixed architecture and object layout
- entrances, exits, paths, obstacles, foreground anchors, and depth layers
- material and main color description
- day/night and practical light sources
- camera-readable spatial geography

Forbidden by default:

- named characters
- combat or story events
- smoke, fire, particles, magic, lens flares, or heavy atmosphere that hides layout
- random extra props that will damage continuity

## Prop asset / 道具资产

- single prop centered
- pure white background
- front or three-quarter view plus necessary detail views
- clear scale, material, wear, construction, and color
- no hands or characters unless required to explain operation

For weapons, define:

- total length and proportion
- blade/head/shaft/guard/grip structure
- material and surface wear
- center of mass or handling character
- sheath, strap, tassel, or accessory when relevant

## Negative constraints / 禁止项

Unless the user asks for them, prohibit:

- text, watermark, logo, UI frame, decorative border
- duplicate body parts or duplicate weapons
- inconsistent face or costume
- cropped body
- perspective distortion that prevents reference use
- motion blur
- movie poster composition
- smoke, flame, glow, particles, spell effects
- extra characters or props

## Output format / 输出格式

When delivering prompts to the user:

- one asset per complete prompt
- include the asset ID and name outside the generation prompt only when useful
- do not include explanations inside the prompt
- do not output a master prompt that requires manual assembly
