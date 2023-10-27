# Shared fixtures

import pytest

from carta.session import Session
from carta.image import Image


@pytest.fixture
def session():
    return Session(0, None)


@pytest.fixture
def image(session):
    return Image(session, 0)


@pytest.fixture
def mock_get_value(mocker):
    def func(obj):
        return mocker.patch.object(obj, "get_value")
    return func


@pytest.fixture
def mock_call_action(mocker):
    def func(obj):
        return mocker.patch.object(obj, "call_action")
    return func


@pytest.fixture
def mock_property(mocker):
    def func_outer(class_path):
        def func_inner(property_name, mock_value):
            return mocker.patch(f"{class_path}.{property_name}", new_callable=mocker.PropertyMock, return_value=mock_value)
        return func_inner
    return func_outer


@pytest.fixture
def mock_method(mocker):
    def func_outer(obj):
        def func_inner(method_name, return_values):
            return mocker.patch.object(obj, method_name, side_effect=return_values)
        return func_inner
    return func_outer
