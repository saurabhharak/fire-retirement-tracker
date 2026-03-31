from app.core.formatting import format_indian

def test_format_small_number():
    assert format_indian(500) == "500"

def test_format_thousands():
    assert format_indian(1250) == "1,250"

def test_format_lakhs():
    assert format_indian(125000) == "1,25,000"

def test_format_crores():
    assert format_indian(10844030) == "1,08,44,030"

def test_format_negative():
    assert format_indian(-50000) == "-50,000"

def test_format_zero():
    assert format_indian(0) == "0"

def test_format_float_rounds():
    assert format_indian(1234.56) == "1,235"
