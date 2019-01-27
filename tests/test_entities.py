import dataclasses
import pytest

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


def test_material_sum():
    m1 = entities.Material('test', 1, 'test')
    m2 = entities.Material('test', 3, 'test')

    result = m1 + m2
    assert isinstance(result, entities.Material)
    assert result is m1
    assert result.count == 4


def test_material_sub():
    m1 = entities.Material('test', 1, 'test')
    m2 = entities.Material('test', 3, 'test')

    result = m2 - m1
    assert isinstance(result, entities.Material)
    assert result is m2
    assert result.count == 2


def test_material_sub_below_zero():
    m1 = entities.Material('test', 1, 'test')
    m2 = entities.Material('test', 3, 'test')

    result = m1 - m2
    assert isinstance(result, entities.Material)
    assert result is m1
    assert result.count == 0


def test_material_sum_different_materials():
    m1 = entities.Material('test', 1, 'test')
    m2 = entities.Material('test2', 3, 'test')

    with pytest.raises(TypeError):
        result = m1 + m2


def test_material_storage_sum_material():
    material_storage = entities.MaterialStorage()
    m = entities.Material('test', 1, 'raw')

    material_storage += m

    assert 'test' in material_storage.raw
    assert material_storage.raw['test'].count == 1

    m2 = entities.Material('test', 2, 'raw')

    material_storage += m2

    assert material_storage.raw['test'].count == 3
