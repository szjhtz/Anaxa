For backend architecture and design patterns:
@./CLAUDE.md

Current backend-specific notes:

- `ask_clarification` is not just a plain text interrupt anymore; the middleware also emits structured clarification payloads consumed by the frontend button card UI.
- `.tex` preview is handled during `present_files` and attempts local compilation through `medrix_flow.utils.latex` with `tectonic`.
- Manuscript citation checks use `citation_audit` and `medrix_flow.utils.citations`; when a sibling `references.bib` exists, `present_files` audits `.tex` citations before PDF compilation.
- Model capability flags such as `supports_thinking`, `supports_reasoning_effort`, and `supports_vision` should be treated as the source of truth for frontend behavior.
