import pytest

from carta.validation import Size, Coordinate


@pytest.mark.parametrize('val', [123, "123arcmin", "123arcsec", "123deg", "123degree", "123degrees", "123px", "123pix", "123pixel", "123pixels", "123 arcmin", "123 arcsec", "123 deg", "123 degree", "123 degrees", "123 px", "123 pix", "123 pixel", "123 pixels", "123", "123\"", "123'"])
def test_size_valid(val):
    v = Size()
    v.validate(val, None)


@pytest.mark.parametrize('val', ["123abc", "abc", "123 \"", "123 '", ""])
def test_size_invalid(val):
    v = Size()
    with pytest.raises(ValueError) as e:
        v.validate(val, None)
    assert "not a number or a numeric string with valid size units" in str(e.value)


@pytest.mark.parametrize('val', [123, 123.4, "123", "123.4", "12:34:56", "12:34:56.7", "01:02:03", "1:02:03", "0:01:02", "00:12:34", "00:00:00", "12:34:5", "12:34:5.678", "12h34m56.789s", "1:2:3", ":1:2", ":12:34", "::1", "::", "1::", ":2:", "12h34m", "10h", "10d", "100d", "10m", "10s", "1.2s", "1m2s", "1h2s", "", "123 deg", "123 degree", "123 degrees"])
def test_coordinate_valid(val):
    v = Coordinate()
    v.validate(val, None)


@pytest.mark.parametrize('val', ["123abc", "abc", "12:345:67", "12:34:567", "12:34", "123:45:67", "hms", "hm", "ms", "h", "m", "s", "hs", "12hms", "12h34ms", "h12m34s", "100h", "12:34:56,7"])
def test_coordinate_invalid(val):
    v = Coordinate()
    with pytest.raises(ValueError) as e:
        v.validate(val, None)
    assert "not a number, a string in H:M:S or D:M:S format, or a numeric string with degree units or pixel units" in str(e.value)
