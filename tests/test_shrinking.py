from typing import Dict
from rekuest.api.schema import adefine
from rekuest.definition.define import prepare_definition
import pytest
from rekuest.structures.registry import StructureRegistry, register_structure

from .structures import SecondSerializableObject, SerializableObject
from .funcs import complex_karl, karl, structured_gen
from rekuest.structures.serialization.postman import (
    shrink_inputs,
    expand_outputs,
    ShrinkingError,
)
from rekuest.structures.serialization.actor import (
    expand_inputs,
)
from .mocks import MockRequestRath


@pytest.fixture
def arkitekt_rath():

    return MockRequestRath()


@pytest.fixture
def simple_registry():

    registry = StructureRegistry()

    register_structure(identifier="hm/test", registry=registry)(SerializableObject)
    register_structure(identifier="hm/karl", registry=registry)(SecondSerializableObject)

    return registry


async def test_shrinking(simple_registry, arkitekt_rath):

    async with arkitekt_rath:
        functional_definition = prepare_definition(
            structured_gen, structure_registry=simple_registry
        )

        node = await adefine(functional_definition, rath=arkitekt_rath)
        args = await shrink_inputs(node, "hallo")
        assert len(args) == 2


@pytest.mark.parametrize(
    ["args", "kwargs"],
    [
        ((["hallo"], {"k": 5}), {"name": "name"}),
        ((["nn", "nn"], {"k": 5}), {"name": "name"}),
        ((["nn", "nn"], {"k": 5}), {}),
    ],
)
async def test_shrinking_complex(args, kwargs, simple_registry, arkitekt_rath):

    async with arkitekt_rath:
        definition = prepare_definition(
            complex_karl, structure_registry=simple_registry
        )

        node = await adefine(definition, rath=arkitekt_rath)

        parsed_args = await shrink_inputs(
            node, args, kwargs, structure_registry=simple_registry
        )
        assert len(parsed_args) == 2, "Args are two short"


@pytest.mark.parametrize(
    ["args", "kwargs"],
    [
        (
            ([SerializableObject(number=4)],),
            {"name": {"k": SerializableObject(number=6)}},
        ),
    ],
)
async def test_shrinking_complex_structure(
    args, kwargs, simple_registry, arkitekt_rath
):
    async with arkitekt_rath:
        definition = prepare_definition(
            structured_gen, structure_registry=simple_registry
        )

        node = await adefine(definition, rath=arkitekt_rath)

        parsed_args = await shrink_inputs(
            node, args, kwargs, structure_registry=simple_registry
        )
        assert len(parsed_args) == 1, "Args are two short"


@pytest.mark.parametrize(
    ["args", "kwargs"],
    [
        (([4],), {"name": {"k": 6}}),
    ],
)
async def test_expanding_complex_structure(
    args, kwargs, simple_registry, arkitekt_rath
):
    async with arkitekt_rath:
        definition = prepare_definition(
            structured_gen, structure_registry=simple_registry
        )

        functional_node = await adefine(definition, rath=arkitekt_rath)

        parsed_args = await expand_inputs(
            functional_node, args, kwargs, structure_registry=simple_registry
        )
        assert len(parsed_args) == 1, "Args are two short"


@pytest.mark.parametrize(
    ["args", "kwargs"],
    [
        (
            ([SerializableObject(number=4)], {"k": SerializableObject(number=7)}),
            {"name": SerializableObject(number=6)},
        ),
    ],
)
async def unpack_pack(args, kwargs, simple_registry, arkitekt_rath):
    async with arkitekt_rath:
        definition = prepare_definition(
            structured_gen, structure_registry=simple_registry
        )
        node = await adefine(definition, rath=arkitekt_rath)

        parsed_args = await shrink_inputs(
            node, args, kwargs, structure_registry=simple_registry
        )
        expanded_args = await expand_inputs(
            node, parsed_args, structure_registry=simple_registry
        )


async def test_shrinking_complex_error(simple_registry, arkitekt_rath):

    async with arkitekt_rath:
        definition = prepare_definition(
            complex_karl, structure_registry=simple_registry
        )
        functional_node = await adefine(definition, rath=arkitekt_rath)

        with pytest.raises(ShrinkingError):
            args, kwargs = await shrink_inputs(
                functional_node,
                ["hallo"],
                {"k": Dict},
                structure_registry=simple_registry,
            )
        with pytest.raises(ShrinkingError):

            args, kwargs = await shrink_inputs(
                functional_node, ["hallo"], 3, structure_registry=simple_registry
            )


async def test_shrinking(simple_registry, arkitekt_rath):

    async with arkitekt_rath:
        definition = prepare_definition(karl, structure_registry=simple_registry)
        functional_node = await adefine(definition, rath=arkitekt_rath)
        args = await shrink_inputs(
            functional_node, ("hallo",), {}, simple_registry
        )


async def test_expanding(simple_registry, arkitekt_rath):
    async with arkitekt_rath:
        definition = prepare_definition(karl, structure_registry=simple_registry)
        functional_node = await adefine(definition, rath=arkitekt_rath)
        expanded = await expand_outputs(functional_node, ["expanded"], simple_registry)
        assert expanded == "expanded"
