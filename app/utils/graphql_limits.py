"""
Limits of the GraphQL endpoint against abusive queries (one request that
costs the server far more than it costs the attacker):

- size: at most MAX_QUERY_CHARS characters and MAX_TOKENS tokens, checked
  before the full parse (parsing is linear in tokens, but unbounded).
- depth: at most MAX_DEPTH nested selections (trip → tickets → trip → …
  cycles exist in the schema).
- breadth: at most MAX_FIELDS field selections in the whole document, and
  at most MAX_ALIASES aliases (the «a1: getTripList … a500:» trick that runs
  the same expensive resolver hundreds of times in one request).
- introspection: off in production (the schema stays private; the frontend
  never needs it). On with DEBUG for local tools.

The frontend's real queries stay far below every limit (the deepest is 3,
the widest about 40 fields).
"""

from typing import List, Type

from django.conf import settings
from graphql import GraphQLError
from graphql.language import (
    FieldNode,
    FragmentDefinitionNode,
    FragmentSpreadNode,
    InlineFragmentNode,
    OperationDefinitionNode,
)
from graphql.validation import ASTValidationRule, NoSchemaIntrospectionCustomRule, ValidationContext
from graphql.validation.specified_rules import specified_rules

MAX_QUERY_CHARS = 12_000
MAX_TOKENS = 2_500
MAX_DEPTH = 8
MAX_FIELDS = 300
MAX_ALIASES = 15


class QueryShapeRule(ASTValidationRule):
    """Depth, total fields and aliases of every operation (fragments expanded)."""

    def __init__(self, context: ValidationContext):
        super().__init__(context)
        self.fragments = {
            d.name.value: d for d in context.document.definitions if isinstance(d, FragmentDefinitionNode)
        }

    def enter_operation_definition(self, node: OperationDefinitionNode, *_args):
        stats = {"fields": 0, "aliases": 0}
        depth = self._walk(node.selection_set, 0, stats, set())
        if depth > MAX_DEPTH:
            self.report_error(GraphQLError(f"Query too deep (max {MAX_DEPTH}).", node))
        if stats["fields"] > MAX_FIELDS:
            self.report_error(GraphQLError(f"Query too large (max {MAX_FIELDS} fields).", node))
        if stats["aliases"] > MAX_ALIASES:
            self.report_error(GraphQLError(f"Too many aliases (max {MAX_ALIASES}).", node))

    def _walk(self, selection_set, depth, stats, seen_fragments) -> int:
        if selection_set is None:
            return depth
        deepest = depth
        for sel in selection_set.selections:
            if isinstance(sel, FieldNode):
                stats["fields"] += 1
                if sel.alias is not None:
                    stats["aliases"] += 1
                deepest = max(deepest, self._walk(sel.selection_set, depth + 1, stats, seen_fragments))
            elif isinstance(sel, InlineFragmentNode):
                deepest = max(deepest, self._walk(sel.selection_set, depth, stats, seen_fragments))
            elif isinstance(sel, FragmentSpreadNode):
                name = sel.name.value
                fragment = self.fragments.get(name)
                # A fragment cycle is reported by the standard rules
                if fragment is None or name in seen_fragments:
                    continue
                deepest = max(
                    deepest, self._walk(fragment.selection_set, depth, stats, seen_fragments | {name})
                )
            if stats["fields"] > MAX_FIELDS * 2:
                break  # already rejected: stop walking a huge document
        return deepest


def validation_rules() -> List[Type[ASTValidationRule]]:
    """The standard GraphQL rules plus ours (passing rules replaces them)."""
    rules = list(specified_rules) + [QueryShapeRule]
    if not settings.DEBUG:
        rules.append(NoSchemaIntrospectionCustomRule)
    return rules
