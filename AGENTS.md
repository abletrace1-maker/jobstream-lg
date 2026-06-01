# Agent Learnings & Preferences

- **LangGraph Checkpoints**: When reading state directly from a compiled graph via `graph.get_state(config)`, the returned object is a `StateSnapshot`. The actual state dictionary is accessed via the `.values` attribute. Use this instead of directly querying the `SqliteSaver` checkpointer for easier access to the structured state representation.
- **LangGraph State Updates**: When updating state to resume from a pause (`interrupt_before`), call `graph.update_state(config, {"key": value})` and then trigger resumption with `graph.stream(None, config)`. Do not use `as_node` unless you want to skip the node entirely, as omitting it naturally steps into the interrupted node.

