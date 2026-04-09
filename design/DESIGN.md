# Design System Specification: Editorial Excellence for SK Telecom

## 1. Overview & Creative North Star
**The Creative North Star: "The Pulse of Innovation"**

To transcend the "standard corporate newsletter," this design system moves away from rigid, boxed-in layouts toward a **high-end editorial experience**. We view the newsletter not as a series of announcements, but as a curated digital magazine. 

The aesthetic is defined by **Soft Minimalism**—where the weight of the design is carried by bold typography and sophisticated tonal layering rather than structural lines. By utilizing intentional asymmetry and expansive breathing room, we reflect SKT’s identity as a leader in cutting-edge connectivity: fast, fluid, and human-centric.

---

## 2. Colors & Tonal Depth
This system leverages a sophisticated palette to move beyond "flat" UI. We use color to imply hierarchy and emotion.

### The Palette
*   **Brand Kinetic:** `primary` (#b90064) and `primary_container` (#e6007e). Use these for moments of high energy and action.
*   **Professional Anchor:** `secondary` (#4e6073) and `on_secondary_fixed` (#091d2e). These provide the "Navy Blue" weight required for corporate trust.
*   **Surface Logic:** A range of grays from `surface_container_lowest` (#ffffff) to `surface_dim` (#d9dadb).

### Core Visual Rules
*   **The "No-Line" Rule:** 1px solid borders are strictly prohibited for sectioning. Differentiation must be achieved through background shifts. Place a `surface_container_lowest` card atop a `surface_container_low` background to define boundaries.
*   **Signature Textures:** For Hero sections, utilize a subtle linear gradient (135°) transitioning from `primary` to `primary_container`. This adds a "soul" to the brand crimson that flat hex codes cannot replicate.
*   **The Glassmorphism Clause:** For floating navigational elements or featured overlays, use `surface` colors at 80% opacity with a `20px` backdrop-blur. This ensures the content feels integrated into the environment rather than "pasted" on top.

---

## 3. Typography: The Editorial Voice
We utilize a dual-typeface system to balance innovation with absolute readability.

*   **Display & Headlines (Manrope):** Chosen for its geometric modernism. Use `display-lg` and `headline-md` to create an authoritative, "newsroom" feel.
*   **Interface & Body (Inter/Apple SD Gothic Neo):** Chosen for its exceptional legibility at small scales.

### Hierarchy Guidelines
*   **The Power Gap:** Create high contrast between headlines and body text. A `headline-lg` title should be immediately followed by `body-md` to emphasize the importance of the lead story.
*   **Tonal Labels:** Use `label-md` in `on_surface_variant` for metadata (dates, categories). This reduces visual noise while maintaining structure.

---

## 4. Elevation & Depth
In this system, "Elevation" is a measure of light and layering, not just shadows.

*   **The Layering Principle:** Stacking order defines importance. 
    1.  Base: `surface` (#f8f9fa)
    2.  Section: `surface_container_low` (#f3f4f5)
    3.  Card/Content: `surface_container_lowest` (#ffffff)
*   **Ambient Shadows:** When a card requires a "lift" (e.g., a featured innovation story), use a diffused shadow: `y-8, blur-24, color: rgba(25, 28, 29, 0.06)`. It should feel like a soft glow of light, not a dark smudge.
*   **Ghost Borders:** If accessibility requires a container edge, use the `outline_variant` token at **15% opacity**. It must be felt, not seen.

---

## 5. Components

### Cards (The Primary Vehicle)
*   **Geometry:** Use `rounded-lg` (1rem/16px) for main containers and `rounded-md` (0.75rem/12px) for inner elements like images.
*   **Spacing:** Enforce a minimum of `2rem` (32px) internal padding. Content needs room to breathe to feel premium.
*   **No Dividers:** Never use horizontal rules (`<hr>`). Use vertical whitespace or a shift to `surface_container_high` to separate content blocks.

### Buttons (The Kinetic Element)
*   **Primary:** Background: `primary_container`; Label: `on_primary`. Shape: `rounded-full` (Pill). This shape suggests "Efficiency" and "Modernity."
*   **Secondary:** Background: `transparent`; Border: `Ghost Border` (outline-variant @ 20%); Label: `primary`. 
*   **Interaction:** On hover, shift background to `primary` (#b90064) for a deep, tactile response.

### Editorial Chips
*   **Usage:** For categorizing news (e.g., "5G", "AI", "ESG").
*   **Styling:** Background: `secondary_container`; Label: `on_secondary_container`. Use `rounded-sm` (4px) to provide a structural counterpoint to the rounded buttons.

### Imagery & Media
*   **Treatment:** All images should feature a `rounded-md` corner radius. 
*   **Overlays:** When placing text over images, use a bottom-up gradient scrim (from `black` @ 60% to `transparent`) to ensure `title-lg` readability.

---

## 6. Do’s and Don’ts

### Do
*   **Do** use asymmetrical margins (e.g., more padding on the left than the right in decorative headers) to create a sense of motion.
*   **Do** prioritize the `primary_container` (Crimson) for high-intent CTAs only.
*   **Do** use `body-lg` for intro paragraphs to hook the reader with an editorial feel.

### Don't
*   **Don't** use 100% black (#000000) for text. Use `on_surface` (#191c1d) to maintain a sophisticated, soft-contrast look.
*   **Don't** crowd the layout. If you think it needs more content, it actually needs more white space.
*   **Don't** use standard "drop shadows" from software defaults. Always tint your shadows with a hint of the brand's navy or crimson to keep them "living."

---

## 7. Accessibility & Integrity
*   **Contrast:** Ensure all `on_surface` text against `surface` containers meets WCAG AA standards (4.5:1).
*   **Readability:** Maintain a maximum line length of 65 characters for body text to prevent eye fatigue.
*   **Scaling:** All components must be defined in `rem` units to respect user font-size preferences in modern email clients.