import dataclasses

from edp import entities


def test_entity_set_sentinel():
    @dataclasses.dataclass()
    class TestEntity(entities._BaseEntity):
        foo: str = '1'

    e = TestEntity()

    assert e.foo == '1'
    e.foo = e.__sentinel__
    assert e.foo == '1'


def test_entity_changed():
    @dataclasses.dataclass()
    class TestEntity(entities._BaseEntity):
        foo: str = '1'

    e = TestEntity()

    assert not e.is_changed
    assert e.foo == '1'
    assert not e.is_changed
    e.foo = '2'
    assert e.is_changed


def test_entity_reset_changed():
    @dataclasses.dataclass()
    class TestEntity(entities._BaseEntity):
        foo: str = '1'

    e = TestEntity()

    e.foo = '2'
    assert e.is_changed
    e.reset_changed()
    assert not e.is_changed


def test_entity_clear():
    @dataclasses.dataclass()
    class NestedEntity(entities._BaseEntity):
        field: dict = dataclasses.field(default_factory=dict)

    @dataclasses.dataclass()
    class TestEntity(entities._BaseEntity):
        foo: str = '1'
        nested: NestedEntity = dataclasses.field(default_factory=NestedEntity)

    e = TestEntity()
    e.foo = '2'
    e.nested.field['1'] = '2'

    assert e.is_changed

    e.clear()

    assert e.foo == '1'
    assert e.nested.field == {}
