# Accessibility

<!-- summary: Semantic markup, keyboard operable, sufficient contrast, labelled controls, ARIA only when needed. -->
<!-- tier: domain -->
<!-- category: Product & Interface -->

If people can't use it, it doesn't work. Accessibility is not a late audit — it
is how you build the interface, and it overlaps almost entirely with just doing
UI correctly.

**Semantic structure first.** Use the right element for the job — a real button,
link, heading, list, and landmark. Native elements come with keyboard behavior,
focus, and screen-reader semantics for free; a `div` pretending to be a button
gives up all of it.

**Keyboard operable.** Everything you can do with a mouse works with a keyboard,
in a sensible focus order, with a visible focus indicator. If you can't tab to it
and activate it, it's broken for a real set of users.

**Sufficient contrast and scalable text.** Meet WCAG contrast ratios for text and
meaningful UI; don't convey meaning by color alone. Layout survives zoom / larger
font sizes without clipping.

**Every control is labelled.** Inputs have associated labels; icon-only buttons
have accessible names; images have alt text (empty alt for purely decorative
ones). Errors are announced, not just shown in red.

**ARIA sparingly, and correctly.** Prefer native semantics; reach for ARIA only
to fill a genuine gap. Wrong ARIA is worse than none — it lies to assistive tech.

**Verify with the tools users use.** Automated checks (axe, Lighthouse) catch the
easy failures; a keyboard-only pass and a screen-reader spot-check catch the ones
that actually matter. Bake the automated check into CI.
