from textwrap import wrap
from typing import Any, Awaitable, Callable, Dict, List
from pydantic import Field
from rekuest.agents.stateful import StatefulAgent
from rekuest.api.schema import TemplateFragment, WidgetInput
from rekuest.postmans.graphql import GraphQLPostman
from rekuest.postmans.stateful import StatefulPostman
from rekuest.rath import RekuestRath
from rekuest.messages import Provision
from rekuest.structures.default import get_default_structure_registry
from rekuest.structures.registry import (
    StructureRegistry,
)

from rekuest.definition.registry import (
    DefinitionRegistry,
    get_current_definition_registry,
)
from rekuest.agents.base import BaseAgent
from rekuest.postmans.base import BasePostman
from koil import unkoil
from koil.composition import Composition
from koil.decorators import koilable


@koilable(fieldname="koil", add_connectors=True)
class Rekuest(Composition):
    rath: RekuestRath = Field(default_factory=RekuestRath)
    structure_registry: StructureRegistry = Field(
        default_factory=get_default_structure_registry
    )
    definition_registry: DefinitionRegistry = Field(
        default_factory=get_current_definition_registry
    )
    agent: BaseAgent = Field(default_factory=StatefulAgent)
    postman: BasePostman = Field(default_factory=GraphQLPostman)

    def register(
        self,
        builder=None,
        widgets: Dict[str, WidgetInput] = {},
        package=None,
        interface=None,
        interfaces: List[str] = [],
        on_provide: Callable[[Provision, TemplateFragment], Awaitable[Any]] = None,
        on_unprovide: Callable[[], Awaitable[Any]] = None,
        structure_registry: StructureRegistry = None,
        **actorparams,
    ) -> None:
        """
        Register a new function
        """
        structure_registry = structure_registry or self.structure_registry

        def real_decorator(function_or_actor):

            self.definition_registry.register(
                function_or_actor,
                builder=builder,
                package=package,
                interface=interface,
                widgets=widgets,
                interfaces=interfaces,
                structure_registry=structure_registry,
                on_provide=on_provide,
                on_unprovide=on_unprovide,
                **actorparams,
            )

            return function_or_actor

        return real_decorator

    def run(self, *args, **kwargs) -> None:
        """
        Run the application.
        """
        return unkoil(self.arun, *args, **kwargs)

    async def arun(self) -> None:
        """
        Run the application.
        """
        assert self.agent.transport.connected, "Transport is not connected"
        await self.agent.aprovide()

    class Config:
        arbitrary_types_allowed = True
        underscore_attrs_are_private = True
        extra = "forbid"
