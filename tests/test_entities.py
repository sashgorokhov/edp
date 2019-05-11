import dataclasses
import pytest
from dpcontracts import PreconditionError
from hypothesis import strategies as st, given

from edp import entities


def test_entity_set_sentinel():
    @dataclasses.dataclass()
    class TestEntity(entities.BaseEntity):
        foo: str = '1'

    e = TestEntity()

    assert e.foo == '1'
    e.foo = e.__sentinel__
    assert e.foo == '1'


def test_entity_changed():
    @dataclasses.dataclass()
    class TestEntity(entities.BaseEntity):
        foo: str = '1'

    e = TestEntity()

    assert not e.is_changed
    assert e.foo == '1'
    assert not e.is_changed
    e.foo = '2'
    assert e.is_changed


def test_entity_reset_changed():
    @dataclasses.dataclass()
    class TestEntity(entities.BaseEntity):
        foo: str = '1'

    e = TestEntity()

    e.foo = '2'
    assert e.is_changed
    e.reset_changed()
    assert not e.is_changed


def test_entity_clear():
    @dataclasses.dataclass()
    class NestedEntity(entities.BaseEntity):
        field: dict = dataclasses.field(default_factory=dict)

    @dataclasses.dataclass()
    class TestEntity(entities.BaseEntity):
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


@given(name=st.text(min_size=1),
       count=st.integers(min_value=1),
       category=st.sampled_from(('Raw', 'manufactured', '$MICRORESOURCE_CATEGORY_Encoded')))
def test_material_storage_add_material(name: str, count: int, category: str):
    storage = entities.MaterialStorage()
    assert storage.add_material(name=name, count=count, category=category) == count


@given(name=st.none() | st.text(max_size=0) | st.integers(),
       count=st.none() | st.integers(max_value=0) | st.text(),
       category=st.none() | st.integers() | st.sampled_from(('Raw', 'manufactured', '$MICRORESOURCE_CATEGORY_Encoded')))
def test_material_storage_add_material_failed_preconditions(name: str, count: int, category: str):
    storage = entities.MaterialStorage()
    with pytest.raises(PreconditionError):
        storage.add_material(name=name, count=count, category=category)


@given(name=st.text(min_size=1),
       category=st.sampled_from(('Raw', 'manufactured', '$MICRORESOURCE_CATEGORY_Encoded')))
@pytest.mark.parametrize(('existing', 'remove', 'result'), [
    (5, 1, 4),
    (5, 5, 0),
    (5, 6, 0),
    (0, 3, 0),
])
def test_material_storage_remove_material(existing, remove, result, name, category):
    storage = entities.MaterialStorage()
    storage[category][name] = existing
    assert storage.remove_material(name, remove, category) == result


@pytest.mark.parametrize('category', ['raw', 'encoded', 'manufactured'])
def test_material_storage_shortcut_access(category):
    storage = entities.MaterialStorage()
    storage[category]['test'] = 5
    assert getattr(storage, category)['test'] == 5
