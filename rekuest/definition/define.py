from contextlib import nullcontext
from enum import Enum
from random import choices
from typing import Any, Callable, List, Tuple
import inflection
from rekuest.api.schema import (
    ArgPortInput,
    ChildPortInput,
    DefinitionInput,
    NodeKindInput,
    PortKindInput,
    ReturnPortInput,
    WidgetInput,
)
import inspect
from docstring_parser import parse
from rekuest.definition.errors import DefinitionError

from rekuest.structures.registry import (
    StructureRegistry,
)


def convert_child_to_childport(
    cls, registry: StructureRegistry, nullable=False, is_return=False
) -> Tuple[ChildPortInput, WidgetInput, Callable]:

    if cls.__module__ == "typing":

        if hasattr(cls, "_name"):
            # We are dealing with a Typing Var?
            if cls._name == "List":
                child, insidewidget, nested_converter = convert_child_to_childport(
                    cls.__args__[0], registry, nullable=False
                )

                return (
                    ChildPortInput(
                        kind=PortKindInput.LIST,
                        child=child,
                        nullable=nullable,
                    ),
                    insidewidget,
                    lambda default: [nested_converter(ndefault) for ndefault in default]
                    if default
                    else None,
                )

            if cls._name == "Dict":
                child, insidewidget, nested_converter = convert_child_to_childport(
                    cls.__args__[1], "omit", registry, nullable=False
                )
                return (
                    ChildPortInput(
                        kind=PortKindInput.DICT,
                        child=child,
                        nullable=nullable,
                    ),
                    insidewidget,
                    lambda default: {
                        key: item in nested_converter(item)
                        for key, item in default.items()
                    }
                    if default
                    else None,
                )

        if hasattr(cls, "__args__"):
            if cls.__args__[1] == type(None):
                return convert_argument_to_port(
                    cls.__args__[0], registry, nullable=True
                )

    if inspect.isclass(cls):
        # Generic Cases

        if not issubclass(cls, Enum) and issubclass(cls, bool):
            t = ChildPortInput(
                kind=PortKindInput.BOOL,
                nullable=nullable,
            )  # catch bool is subclass of int
            return t, None, str

        if not issubclass(cls, Enum) and issubclass(cls, int):
            return (
                ChildPortInput(
                    kind=PortKindInput.INT,
                    nullable=nullable,
                ),
                None,
                int,
            )
        if not issubclass(cls, Enum) and issubclass(cls, str):
            return (
                ChildPortInput(
                    kind=PortKindInput.STRING,
                    nullable=nullable,
                ),
                None,
                str,
            )

    identifier = registry.get_identifier_for_structure(cls)
    default_converter = registry.get_default_converter_for_structure(cls)
    widget = (
        registry.get_returnwidget_input(cls)
        if is_return
        else registry.get_widget_input(cls)
    )

    return (
        ChildPortInput(
            kind=PortKindInput.STRUCTURE,
            identifier=identifier,
            nullable=nullable,
        ),
        widget,
        default_converter,
    )


def convert_argument_to_port(
    cls,
    key,
    registry: StructureRegistry,
    widget=None,
    default=None,
    nullable=False,
    annotations=[],
) -> ArgPortInput:
    """
    Convert a class to an ArgPort
    """
    if hasattr(cls, "__name__") and cls.__name__ == "Annotated":
        real_type = cls.__args__[0]

        annotations = [
            registry.get_converter_for_annotation(i.__class__)(i)
            for i in cls.__metadata__
        ]

        return convert_argument_to_port(
            real_type,
            key,
            registry,
            widget=widget,
            default=default,
            nullable=nullable,
            annotations=annotations,
        )

    if cls.__module__ == "typing":

        if hasattr(cls, "_name"):
            # We are dealing with a Typing Var?
            if cls._name == "List":
                child, widget, converter = convert_child_to_childport(
                    cls.__args__[0], registry, nullable=False
                )
                return ArgPortInput(
                    kind=PortKindInput.LIST,
                    widget=widget,
                    key=key,
                    child=child.dict(exclude={"key"}),
                    default=[converter(item) for item in default] if default else None,
                    nullable=nullable,
                    annotations=annotations,
                )

            if cls._name == "Dict":
                child, widget, converter = convert_child_to_childport(
                    cls.__args__[1], registry, nullable=False
                )
                return ArgPortInput(
                    kind=PortKindInput.DICT,
                    widget=widget,
                    key=key,
                    child=child.dict(exclude={"key"}),
                    default={key: converter(item) for key, item in default.items()},
                    nullable=nullable,
                    annotations=annotations,
                )

            if cls._name == "Union":
                raise NotImplementedError("Union is not supported yet")

        if hasattr(cls, "__args__"):
            if cls.__args__[1] == type(None):
                return convert_argument_to_port(
                    cls.__args__[0], key, registry, default=default, nullable=True
                )

    if inspect.isclass(cls):
        # Generic Cases

        if (
            not issubclass(cls, Enum)
            and issubclass(cls, bool)
            or (default is not None and isinstance(default, bool))
        ):
            t = ArgPortInput(
                kind=PortKindInput.BOOL,
                widget=widget,
                key=key,
                default=default,
                nullable=nullable,
                annotations=annotations,
            )  # catch bool is subclass of int
            return t

        if (
            not issubclass(cls, Enum)
            and issubclass(cls, int)
            or (default is not None and isinstance(default, int))
        ):
            return ArgPortInput(
                kind=PortKindInput.INT,
                widget=widget,
                key=key,
                default=default,
                nullable=nullable,
                annotations=annotations,
            )

        if (
            not issubclass(cls, Enum)
            and issubclass(cls, float)
            or (default is not None and isinstance(default, float))
        ):
            return ArgPortInput(
                kind=PortKindInput.FLOAT,
                widget=widget,
                key=key,
                default=default,
                nullable=nullable,
                annotations=annotations,
            )

        if (
            not issubclass(cls, Enum)
            and issubclass(cls, str)
            or (default is not None and isinstance(default, str))
        ):
            return ArgPortInput(
                kind=PortKindInput.STRING,
                widget=widget,
                key=key,
                default=default,
                nullable=nullable,
                annotations=annotations,
            )

    identifier = registry.get_identifier_for_structure(cls)
    default_converter = registry.get_default_converter_for_structure(cls)
    widget = widget or registry.get_widget_input(cls)

    return ArgPortInput(
        kind=PortKindInput.STRUCTURE,
        identifier=identifier,
        widget=widget,
        key=key,
        default=default_converter(default) if default else None,
        nullable=nullable,
        annotations=annotations,
    )


def convert_return_to_returnport(
    cls, key: str, registry: StructureRegistry, widget=None, nullable=False
) -> ReturnPortInput:
    """
    Convert a class to an ArgPort
    """

    if cls.__module__ == "typing":

        if hasattr(cls, "_name"):
            # We are dealing with a Typing Var?
            if cls._name == "List":
                child, widget, converter = convert_child_to_childport(
                    cls.__args__[0], registry, nullable=False, is_return=True
                )
                return ReturnPortInput(
                    kind=PortKindInput.LIST,
                    widget=widget,
                    key=key,
                    child=child.dict(exclude={"key"}),
                    nullable=nullable,
                )

            if cls._name == "Dict":
                child, widget, converter = convert_child_to_childport(
                    cls.__args__[1], registry, nullable=False, is_return=True
                )
                return ReturnPortInput(
                    kind=PortKindInput.DICT,
                    widget=widget,
                    key=key,
                    child=child.dict(exclude={"key"}),
                    nullable=nullable,
                )

        if hasattr(cls, "__args__"):
            if cls.__args__[1] == type(None):
                return convert_return_to_returnport(
                    cls.__args__[0], key, registry, nullable=True
                )

    if inspect.isclass(cls):
        # Generic Cases

        if issubclass(cls, bool):
            return ReturnPortInput(
                kind=PortKindInput.BOOL, key=key, nullable=nullable
            )  # catch bool is subclass of int
        if issubclass(cls, Enum):
            return ReturnPortInput(
                kind=PortKindInput.ENUM,
                key=key,
                options={key: value._value_ for key, value in cls.__members__.items()},
                nullable=nullable,
            )
        if issubclass(cls, int):
            return ReturnPortInput(kind=PortKindInput.INT, key=key, nullable=nullable)
        if issubclass(cls, float):
            return ReturnPortInput(kind=PortKindInput.FLOAT, key=key, nullable=nullable)
        if issubclass(cls, str):
            return ReturnPortInput(
                kind=PortKindInput.STRING, key=key, nullable=nullable
            )

    identifier = registry.get_identifier_for_structure(cls)
    widget = widget or registry.get_returnwidget_input(cls)

    return ReturnPortInput(
        kind=PortKindInput.STRUCTURE,
        identifier=identifier,
        key=key,
        widget=widget,
        nullable=nullable,
    )


def prepare_definition(
    function: Callable,
    package=None,
    interface=None,
    widgets={},
    allow_empty_doc=False,
    interfaces=[],
    structure_registry: StructureRegistry = None,
    omitfirst=None,
    omitlast=None,
    omitkeys=[],
) -> DefinitionInput:
    """Define

    Define a functions in the context of arnheim and
    return it as a Node. Attention this node is not yet
    hosted on Arkitekt (doesn't have an id). So make sure
    to save this node before calling it anywhere

    Args:
        function (): The function you want to define
    """

    assert structure_registry is not None, "You need to pass a StructureRegistry"

    is_generator = inspect.isasyncgenfunction(function) or inspect.isgeneratorfunction(
        function
    )

    sig = inspect.signature(function)

    # Generate Args and Kwargs from the Annotation
    args: List[ArgPortInput] = []
    returns: List[ReturnPortInput] = []

    function_ins_annotation = sig.parameters

    for index, (key, value) in enumerate(function_ins_annotation.items()):

        # We can skip arguments if the builder is going to provide additional arguments
        if omitfirst is not None and index < omitfirst:
            continue
        if omitlast is not None and index > omitlast:
            continue
        if key in omitkeys:
            continue

        widget = widgets.get(key, None)
        cls = value.annotation

        try:
            args.append(
                convert_argument_to_port(
                    cls,
                    key,
                    structure_registry,
                    widget=widget,
                    default=value.default
                    if value.default != inspect.Parameter.empty
                    else None,
                )
            )
        except Exception as e:
            raise DefinitionError(
                f"Could not convert Argument of function {function.__name__} to ArgPort: {value}"
            ) from e

    function_outs_annotation = sig.return_annotation

    if hasattr(function_outs_annotation, "_name"):

        if function_outs_annotation._name == "Tuple":
            try:
                for index, cls in enumerate(function_outs_annotation.__args__):
                    widget = widgets.get(f"return{index}", None)
                    returns.append(
                        convert_return_to_returnport(
                            cls, f"return{index}", structure_registry
                        )
                    )
            except Exception as e:
                raise DefinitionError(
                    f"Could not convert Return of function {function.__name__} to ArgPort: {cls}"
                ) from e
        else:
            try:
                widget = widgets.get(f"return0", None)
                returns.append(
                    convert_return_to_returnport(
                        function_outs_annotation,
                        f"return0",
                        structure_registry,
                        widget=widget,
                    )
                )  # Other types will be converted to normal lists and shit
            except Exception as e:
                raise DefinitionError(
                    f"Could not convert Return of function {function.__name__} to ArgPort: {function_outs_annotation}"
                ) from e
    else:
        # We are dealing with a non tuple return
        if function_outs_annotation is None:
            pass

        elif function_outs_annotation.__name__ != "_empty":  # Is it not empty
            widget = widgets.get(f"return0", None)
            returns.append(
                convert_return_to_returnport(
                    function_outs_annotation,
                    "return0",
                    structure_registry,
                    widget=widget,
                )
            )

    # Documentation Parsing

    # Docstring Parser to help with descriptions
    docstring = parse(function.__doc__)
    if docstring.long_description is None:
        assert (
            allow_empty_doc is not False
        ), f"We don't allow empty documentation for function {function.__name__}. Please Provide"

    name = docstring.short_description or function.__name__
    interface = interface or inflection.underscore(
        function.__name__
    )  # convert this to camelcase
    description = docstring.long_description or "No Description"

    doc_param_map = {
        param.arg_name: {"description": param.description} for param in docstring.params
    }

    # TODO: Update with documentatoin.... (Set description for portexample)

    doc_returns_map = {
        f"return{index}": {"description": param.description, "label": param.return_name}
        for index, param in enumerate(docstring.many_returns)
    }

    for port in args:
        if port.key in doc_param_map:
            updates = doc_param_map[port.key]
            port.description = updates["description"] or port.description

    for port in returns:
        if port.key in doc_returns_map:
            updates = doc_returns_map[port.key]
            port.description = updates["description"] or port.description

    x = DefinitionInput(
        **{
            "name": name,
            "interface": interface,
            "package": package,
            "description": description,
            "args": args,
            "returns": returns,
            "kind": NodeKindInput.GENERATOR if is_generator else NodeKindInput.FUNCTION,
            "interfaces": interfaces,
        }
    )

    return x
