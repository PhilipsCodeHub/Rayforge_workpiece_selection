"""Tests for the GTK-free extension logic."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from workpiece_selection import extension  # noqa: E402
from workpiece_selection.extension import (  # noqa: E402
    TAB_METHOD,
    extend_registered_pages,
    wrap_page_class,
)


class FakeRegistry:
    def __init__(self, pages):
        self.pages = dict(pages)
        self.addons = {}

    def get(self, name):
        return self.pages.get(name)

    def register(self, name, cls, addon_name=None):
        self.pages[name] = cls
        self.addons[name] = addon_name


class Base:
    extra_pages = (("laser_page", "Laser", "laser-on-symbolic"),)

    def __init__(self, editor, step):
        self.editor, self.step = editor, step

    def laser_page(self):
        return "laser"

    def own_method(self):
        return "inherited"


class NoTabs:
    pass


def setup_function(_fn):
    extension._wrapped_cache.clear()


def test_keeps_base_tabs_and_appends_ours():
    wrapped = wrap_page_class(Base)
    names = [entry[0] for entry in wrapped.extra_pages]
    assert names == ["laser_page", TAB_METHOD]
    assert Base.extra_pages == (("laser_page", "Laser", "laser-on-symbolic"),)


def test_inherits_base_behaviour():
    page = wrap_page_class(Base)("ed", "st")
    assert page.own_method() == "inherited"
    assert page.laser_page() == "laser"
    assert issubclass(type(page), Base)


def test_works_for_class_without_extra_pages():
    wrapped = wrap_page_class(NoTabs)
    assert [e[0] for e in wrapped.extra_pages] == [TAB_METHOD]


def test_wrapping_is_idempotent():
    wrapped = wrap_page_class(Base)
    assert wrap_page_class(wrapped) is wrapped
    assert wrap_page_class(Base) is wrapped  # cached


def test_extend_replaces_registration_under_our_addon_name():
    reg = FakeRegistry({"contour": Base})
    done = extend_registered_pages(reg, ("contour",), "workpiece_selection")
    assert done == ["contour"]
    assert issubclass(reg.pages["contour"], Base)
    assert reg.addons["contour"] == "workpiece_selection"


def test_second_run_does_not_double_wrap():
    reg = FakeRegistry({"contour": Base})
    extend_registered_pages(reg, ("contour",), "a")
    first = reg.pages["contour"]
    assert extend_registered_pages(reg, ("contour",), "a") == []
    assert reg.pages["contour"] is first
    # Laser re-registers the original on a hook re-run; we re-extend it
    # to the same cached class.
    reg.pages["contour"] = Base
    extend_registered_pages(reg, ("contour",), "a")
    assert reg.pages["contour"] is first


def test_missing_assembler_is_skipped():
    reg = FakeRegistry({})
    assert extend_registered_pages(reg, ("contour",), "a") == []
    assert reg.pages == {}


def test_multiple_assemblers_independent():
    class Other(Base):
        pass

    reg = FakeRegistry({"contour": Base, "raster": Other})
    done = extend_registered_pages(reg, ("contour", "raster"), "a")
    assert done == ["contour", "raster"]
    assert reg.pages["contour"] is not reg.pages["raster"]
