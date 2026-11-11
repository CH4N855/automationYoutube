# YouTube Automator desktop UI

CustomTkinter / Windows desktop. Dark slate workspace with coral primary actions,
quiet secondary controls, and text labels for navigation and status.

The ui-ux-pro-max search matched an operations dashboard palette. This app adapts
its slate surfaces and readable status colors to native controls; it does not use
the suggested marketing layout, web fonts, or backdrop blur.

- Theme colors: `src/ui/theme.py`. Native widget defaults: `src/ui/studio-theme.json`.
- Typography: Segoe UI, 12–14px supporting text, 20–30px headings.
- Spacing: 8px control gaps; 16–24px section gutters and card padding.
- Controls: 40–48px action heights, visible labels, distinct disabled states.
- Navigation: persistent sidebar, selected-page background, Ctrl+1 through Ctrl+6.
- Layout: 1060×700 minimum; upload columns stack when available width is under 840px.
- Color always accompanies status text. Failed queue items expose the error and Retry.
- Generation feedback and activity updates are dispatched to the Tk main thread.
- No decorative motion; activity logs are read-only.

Verification: `python tests/preview_ui.py --check` opens each screen at both supported
sizes without starting the scheduler or uploads. `python tests/preview_ui.py` opens
an offline preview. Desktop screenshot verification requires working app capture.
