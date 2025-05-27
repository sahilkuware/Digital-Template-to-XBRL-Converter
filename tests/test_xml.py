import pytest

from mireport.exceptions import BrokenNamespacePrefixException, BrokenQNameException
from mireport.xml import NamespaceManager, QNameMaker


@pytest.fixture
def namespaces() -> NamespaceManager:
    return NamespaceManager()


@pytest.fixture
def xbrli_and_utr() -> NamespaceManager:
    a = NamespaceManager()
    a.add("xbrli", "http://www.xbrl.org/2003/instance")
    a.add("utr", "http://www.xbrl.org/2009/utr")
    return a


@pytest.fixture
def qmaker(xbrli_and_utr: NamespaceManager) -> QNameMaker:
    a = QNameMaker(xbrli_and_utr)
    return a


def test_add_not_uri(namespaces: NamespaceManager) -> None:
    namespaces.add("abc", "http://mushroom")


def test_add_none_str(namespaces: NamespaceManager) -> None:
    with pytest.raises(BrokenNamespacePrefixException):
        namespaces.add(None, "hedgehog")


def test_expected_qname(qmaker: QNameMaker) -> None:
    with pytest.raises(BrokenQNameException):
        qmaker.fromString("abc:def")


def test_unprefixed_qname(qmaker: QNameMaker) -> None:
    with pytest.raises(BrokenQNameException):
        qmaker.fromString(None)


def test_generate_prefix(namespaces: NamespaceManager) -> None:
    p0 = namespaces.getOrGeneratePrefixForNamespace("http://example.com/n0")
    assert p0 == "ns0"
    n1 = "http://example.com/n1"
    namespaces.add("ns1", n1)
    p1 = namespaces.getPrefixForNamespace(n1)
    p2 = namespaces.getOrGeneratePrefixForNamespace("http://example.com/n2")
    assert p1 != p2


def test_valid_qname(qmaker: QNameMaker) -> None:
    qmaker.fromString("xbrli:pure")
    qmaker.fromString("utr:badger")


def test_add_namespace(xbrli_and_utr: NamespaceManager) -> None:
    p = NamespaceManager()
    ns = "http://example.com"
    p1 = p.getOrGeneratePrefixForNamespace(ns)
    assert p1 == p.getPrefixForNamespace(ns)
    assert len(p._prefixToNamespaces) == 1
    p.add(p1, ns)
    assert len(p._prefixToNamespaces) == 1
    p.add("p2", ns)
    assert len(p._prefixToNamespaces) == 2
    pG = p.getOrGeneratePrefixForNamespace(ns)
    assert p1 == pG
    assert p1 is pG, "String interning has been broken."
