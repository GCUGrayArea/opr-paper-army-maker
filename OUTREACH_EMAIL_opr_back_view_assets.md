# Draft email to One Page Rules

Draft for the user to review, edit, and send from their own address — not sent by
the assistant. Placeholders in `[brackets]` need filling in before sending.

---

**Subject:** Fan tool for auto-generating print-ready paper mini sheets from Army Forge lists — request for back-view token art

Hi OPR team,

I'm building a small free fan tool that takes an army list from Army Forge and automatically generates a single print-ready PDF containing exactly the paper miniatures needed for that list — right units, right loadouts, right counts, nothing more. The problem it's solving: right now, building a paper-mini army means manually hunting through a 50–70 page, non-searchable PDF to find the right pages for each unit and loadout, then assembling them yourself before sending to a print shop. That's a real barrier for someone trying to play their first game with paper minis instead of waiting on painted models — my goal is to get that friction as close to zero as possible.

While building this, I found that your paper-mini releases come bundled with VTT token art (the flat, front-facing PNGs meant for virtual tabletop use) alongside the print PDFs. Those turned out to be a much better building block than the PDFs themselves: they're already isolated per unit/loadout with clean transparent backgrounds, whereas parsing the print PDFs (rotated banner labels, dense page grids, mixed color/BW layouts) has been the hardest and most fragile part of this project by far.

Using the VTT art also lets us lay minis out ourselves rather than reusing the PDF's fixed grid — which means packing them more densely and cutting down on paper and print-shop cost for whoever's ordering, on top of removing the manual page-hunting entirely.

The one piece we're missing: the VTT packs only include front views. We can technically try to extract matching back-view crops out of the print PDFs, but that's exactly the fragile parsing step we're trying to get away from. **Would you be willing to share back-view PNGs (same style as the front views — transparent background, one per unit/loadout, both color and black-and-white) for the armies you've released paper-mini packs for?** We'd be glad to start with whichever ones are easiest for you to pull together, or a specific army if you'd rather pilot with one first.

We're building this as a free, open tool for the community — not a commercial product, and not trying to replace or compete with anything you sell. Happy to share the finished tool/source with you once it's working, credit OPR prominently, and of course keep the actual mini artwork usage scoped however you'd like (e.g. bundled per-user download rather than redistributed outright, if that's a concern).

Thanks for considering it, and for the paper-mini packs in the first place — they're what made this project possible at all.

[Your name]
[Contact info / project link]
