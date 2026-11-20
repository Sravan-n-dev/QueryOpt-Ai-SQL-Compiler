"""
Tests for Relational Algebra conversion and nodes.
"""

from compiler.parser import SQLParser
from relational_algebra.converter import ASTToRAConverter
from relational_algebra.nodes import Join, Limit, Projection, Scan, Selection


def test_ra_conversion():
    parser = SQLParser()
    converter = ASTToRAConverter()

    ast = parser.parse("SELECT name FROM Student WHERE age > 23 LIMIT 10")
    ra = converter.convert(ast)

    assert isinstance(ra, Limit)
    assert isinstance(ra.child, Projection)
    assert isinstance(ra.child.child, Selection)
    assert isinstance(ra.child.child.child, Scan)
