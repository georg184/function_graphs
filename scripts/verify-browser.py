"""Verify offline controls, URL presets, saved states and actual MuWeb composition."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import Frame, Page, expect, sync_playwright


def ready(surface: Page | Frame) -> None:
    """Wait for an initialized application with a completely drawn formula.

    Args:
        surface: Application page or opaque sandbox frame.
    """
    expect(surface.locator('#app[data-ready="true"]')).to_be_visible(timeout=30000)
    expect(surface.locator('#function-curve')).to_have_count(1)
    assert not surface.locator('#notice').inner_text()


def slider(surface: Page | Frame, key: str, value: float) -> None:
    """Exercise the production slider event path.

    Args:
        surface: Application page or sandbox frame.
        key: Active parameter identifier.
        value: Requested slider value within its range.
    """
    surface.locator(f'#slider-{key}').evaluate('(el,value)=>{el.value=value;el.dispatchEvent(new Event("input",{bubbles:true}));}', value)


def app_frame(page: Page) -> Frame:
    """Find a production application frame after the host has initialized it.

    Args:
        page: Parent browser page containing one visible application frame.
    """
    page.wait_for_function('() => Array.from(document.querySelectorAll("iframe")).some(frame=>frame.src.startsWith("blob:"))')
    for _ in range(100):
        sources = page.locator('iframe:visible').evaluate_all('(frames)=>frames.map(frame=>frame.src)')
        for frame in page.frames[1:]:
            if frame.url in sources and frame.locator('#app').count():
                ready(frame)
                return frame
        page.wait_for_timeout(100)
    raise AssertionError('No application frame')


def comparison(surface: Page | Frame) -> None:
    """Verify two distinct graphs, a shared coefficient and degenerate cases.

    Args:
        surface: Ready power-function page or embedded frame.
    """
    # Keyboard input also exercises frames scaled by the host's document zoom;
    # Playwright's pointer coordinates omit that ancestor zoom in Chromium.
    if not surface.locator('#comparison-toggle').is_checked():
        surface.locator('#comparison-toggle').press('Space')
    slider(surface, 'n', 4)
    slider(surface, 'm', 2)
    slider(surface, 'a', -2)
    expect(surface.locator('#formula')).to_have_attribute('data-tex', 'f(x)=-2x^{4}')
    expect(surface.locator('#comparison-formula')).to_have_attribute('data-tex', 'g(x)=-2x^{2}')
    expect(surface.locator('#comparison-curve')).to_have_attribute('stroke-dasharray', '8 5')
    assert surface.locator('#function-curve').get_attribute('d') != surface.locator('#comparison-curve').get_attribute('d')
    slider(surface, 'a', 0.5)
    expect(surface.locator('#formula')).to_have_attribute('data-tex', 'f(x)=0.5x^{4}')
    expect(surface.locator('#comparison-formula')).to_have_attribute('data-tex', 'g(x)=0.5x^{2}')
    slider(surface, 'm', 4)
    expect(surface.locator('#comparison-formula')).to_have_attribute('data-tex', 'g(x)=0.5x^{4}')
    expect(surface.locator('#comparison-curve')).to_have_attribute('d', surface.locator('#function-curve').get_attribute('d'))
    slider(surface, 'a', 0)
    expect(surface.locator('#formula')).to_have_attribute('data-tex', 'f(x)=0')
    expect(surface.locator('#comparison-formula')).to_have_attribute('data-tex', 'g(x)=0')
    expect(surface.locator('#insight')).to_contain_text('keine Potenzfunktion.')
    slider(surface, 'a', -2)
    slider(surface, 'm', 2)
    surface.locator('[value="linear"]').press('Space')
    expect(surface.locator('#power-comparison')).to_be_hidden()
    expect(surface.locator('#comparison-formula')).to_be_hidden()
    expect(surface.locator('#comparison-curve')).to_have_count(0)
    assert surface.locator('#slider-m').count() == 1
    surface.locator('[value="power"]').press('Space')
    expect(surface.locator('#comparison-toggle')).to_be_checked()
    expect(surface.locator('#slider-m')).to_have_value('2')
    expect(surface.locator('#comparison-formula')).to_have_attribute('data-tex', 'g(x)=-2x^{2}')
    surface.locator('#comparison-toggle').press('Space')
    expect(surface.locator('#slider-m')).to_be_hidden()
    expect(surface.locator('#comparison-curve')).to_have_count(0)


def main() -> None:
    """Run deterministic browser interactions with all network requests blocked."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--only', choices=('standalone', 'host', 'pyhtml', 'failures'))
    parser.add_argument('--browser', default='/usr/bin/google-chrome')
    args = parser.parse_args()
    directory = args.directory.resolve()
    reports = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser, headless=True, args=['--no-sandbox'])
        context = browser.new_context(viewport={'width': 1500, 'height': 1100})
        context.route('https://**/*', lambda route: route.abort())
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        if args.only in (None, 'standalone'):
            path = (directory / 'standalone.html').as_uri()
            for family, controls in [('linear', ['m', 'q']), ('quadratic', ['a', 'b', 'c']), ('power', ['a', 'n'])]:
                page.goto(path + '?type=' + family)
                ready(page)
                expect(page.locator('input[name="function-type"]:checked')).to_have_value(family)
                assert page.locator('#parameters input[type="range"]').evaluate_all('(inputs)=>inputs.map(input=>input.id)') == ['slider-' + key for key in controls]
                assert page.locator('[name="function-type"]').count() == 3
            original = page.locator('#function-curve').get_attribute('d')
            slider(page, 'a', -2)
            slider(page, 'n', 4)
            expect(page.locator('#formula')).to_have_attribute('data-tex', 'f(x)=-2x^{4}')
            assert original != page.locator('#function-curve').get_attribute('d')
            comparison(page)
            page.locator('#comparison-toggle').focus()
            page.keyboard.press('Space')
            expect(page.locator('#comparison-curve')).to_have_count(1)
            page.screenshot(path=str(directory / 'desktop-power.png'), full_page=True)
            page.reload(); ready(page)
            expect(page.locator('#comparison-toggle')).to_be_checked()
            expect(page.locator('#comparison-formula')).to_have_attribute('data-tex', 'g(x)=-2x^{2}')
            page.locator('[value="linear"]').check()
            slider(page, 'm', 2)
            slider(page, 'q', -3)
            expect(page.locator('#formula')).to_have_attribute('data-tex', 'f(x)=2x-3')
            page.locator('[value="quadratic"]').check()
            slider(page, 'a', 0)
            expect(page.locator('#insight')).to_have_attribute('data-special', 'true')
            page.locator('[value="power"]').check()
            expect(page.locator('#slider-n')).to_have_value('4')
            expect(page.locator('#slider-a')).to_have_value('-2')
            slider(page, 'a', 0)
            expect(page.locator('#insight')).to_contain_text('Nullfunktion')
            page.locator('#number-n').fill('2.5')
            page.locator('#number-n').press('Enter')
            expect(page.locator('#slider-n')).to_have_value('3')
            page.locator('#reset-parameters').click()
            expect(page.locator('#slider-a')).to_have_value('1')
            for _ in range(4):
                page.locator('#zoom-in').click()
            expect(page.locator('#zoom-in')).to_be_disabled()
            page.locator('#reset-view').click()
            page.reload(); ready(page)
            expect(page.locator('[value="power"]')).to_be_checked()
            page.goto(path + '?type=linear'); ready(page)
            expect(page.locator('[value="linear"]')).to_be_checked()
            expect(page.locator('#slider-q')).to_have_value('-3')
            page.locator('[value="linear"]').focus()
            page.keyboard.press('ArrowDown')
            expect(page.locator('[value="quadratic"]')).to_be_checked()
            page.set_viewport_size({'width': 390, 'height': 844})
            page.locator('[value="power"]').check()
            expect(page.locator('#formula')).to_have_attribute('data-tex', 'f(x)=x^{3}')
            expect(page.locator('#comparison-formula')).to_have_attribute('data-tex', 'g(x)=x^{2}')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Mobile horizontal overflow'
            page.screenshot(path=str(directory / 'mobile-power.png'), full_page=True)
            page.set_viewport_size({'width': 1500, 'height': 1100})
            legacy = page.evaluate('FunctionGraphsCore.createState()')
            legacy['schema'] = 1
            del legacy['comparison']
            del legacy['parameters']['power']['m']
            legacy['parameters']['power']['n'] = 7
            page.evaluate('state=>localStorage.setItem("function-graphs-state-v1",JSON.stringify(state))', legacy)
            page.reload(); ready(page)
            expect(page.locator('#slider-n')).to_have_value('7')
            expect(page.locator('#comparison-toggle')).not_to_be_checked()
            reports.append('standalone: presets, controls, comparison/shared coefficient, zero/equal degrees, keyboard, state migration, zoom, mobile')
        if args.only in (None, 'host'):
            page.goto((directory / 'host.html').as_uri())
            frame = app_frame(page)
            comparison(frame)
            frame.locator('#comparison-toggle').check()
            slider(frame, 'n', 11)
            slider(frame, 'a', -0.5)
            page.wait_for_function('() => fixture.state?.parameters.power.n===11 && fixture.state.parameters.power.a===-0.5')
            saved = page.evaluate('fixture.state')
            page.evaluate('state=>fixture.mount({state,activity:"power",presentation:"full",typography:{fontSizePt:13,lineHeight:1.6,scaleFactor:1.3}})', saved)
            frame = app_frame(page)
            expect(frame.locator('#slider-n')).to_have_value('11')
            expect(frame.locator('#formula')).to_have_attribute('data-tex', 'f(x)=-0.5x^{11}')
            expect(frame.locator('#comparison-toggle')).to_be_checked()
            expect(frame.locator('#comparison-formula')).to_have_attribute('data-tex', 'g(x)=-0.5x^{2}')
            assert frame.evaluate('MuWeaveModuleBridge.getTypography().fontSizePt') == 13
            assert frame.evaluate('getComputedStyle(document.body).fontSize') == '17.3333px'
            page.evaluate('state=>fixture.mount({state,activity:"power",launchParameters:{type:"linear"}})', saved)
            frame = app_frame(page)
            expect(frame.locator('[value="linear"]')).to_be_checked()
            frame.locator('[value="power"]').check()
            expect(frame.locator('#slider-n')).to_have_value('11')
            expect(frame.locator('#slider-a')).to_have_value('-0.5')
            page.evaluate('state=>fixture.mount({state,activity:"power",launchParameters:{type:"invalid"}})', saved)
            frame = app_frame(page)
            expect(frame.locator('[value="power"]')).to_be_checked()
            for family in ['linear', 'quadratic', 'power']:
                page.evaluate('activity=>fixture.mount({activity})', family)
                frame = app_frame(page)
                expect(frame.locator('[name="function-type"]:checked')).to_have_value(family)
            legacy = json.loads(json.dumps(saved))
            legacy['schema'] = 1
            del legacy['comparison']
            del legacy['parameters']['power']['m']
            page.evaluate('state=>fixture.mount({state,migrate:true})', legacy)
            frame = app_frame(page)
            expect(frame.locator('#slider-n')).to_have_value('11')
            expect(frame.locator('#comparison-toggle')).not_to_be_checked()
            assert page.evaluate('fixture.state.schema') == 2
            assert page.evaluate('fixture.messages.some(message=>message.kind==="migration-result" && message.payload.ok)')
            page.evaluate('fixture.send("host-disabled",{reason:"verification"})')
            expect(frame.locator('#slider-a')).to_be_disabled()
            expect(frame.locator('#notice')).to_contain_text('gesperrt')
            page.evaluate('fixture.mount({state:{schema:99}})')
            page.wait_for_timeout(500)
            frame = next(frame for frame in page.frames[1:] if frame.locator('#app').count())
            expect(frame.locator('#notice')).to_contain_text('ungültig')
            assert page.evaluate('fixture.state.schema') == 99
            reports.append('host: opaque sandbox, activities, compact/full, comparison restore, bridge migration, typography, disabled/invalid state')
        if args.only in (None, 'pyhtml'):
            page.goto((directory / 'smoke.html').as_uri())
            frame = app_frame(page)
            expect(frame.locator('[value="power"]')).to_be_checked()
            comparison(frame)
            slider(frame, 'a', 1)
            slider(frame, 'n', 6)
            expect(frame.locator('#formula')).to_have_attribute('data-tex', 'f(x)=x^{6}')
            # With no document-level mathematics the shared runtime is stored
            # only in the host profile table and executed inside each sandbox.
            assert page.locator('#muweave-mathjax').count() <= 1
            assert frame.locator('#muweave-mathjax').count() == 1
            assert page.locator('#muweave-runtime-profiles').count() == 1
            page.screenshot(path=str(directory / 'pyhtml.png'), full_page=True)
            with context.expect_page() as pending:
                page.locator('[data-muweave-applet-open]').click()
            popup = pending.value
            popup.on('pageerror', lambda error: errors.append(str(error)))
            popup.wait_for_load_state()
            child = app_frame(popup)
            expect(child.locator('[value="quadratic"]')).to_be_checked()
            slider(child, 'a', -2)
            slider(child, 'c', 3)
            expect(child.locator('#formula')).to_have_attribute('data-tex', 'f(x)=-2x^{2}+3')
            popup.locator('[data-applet-fullscreen]:visible').click()
            expect(popup.locator('.muweave-applet-fullscreen')).to_have_count(1)
            expect(child.locator('#slider-a')).to_have_value('-2')
            popup.locator('[data-applet-exit]:visible').click()
            expect(popup.locator('.muweave-applet-fullscreen')).to_have_count(0)
            expect(child.locator('#slider-c')).to_have_value('3')
            if popup.evaluate('document.documentElement.scrollHeight > innerHeight + 20'):
                popup.evaluate('scrollTo(0,0)')
                child.locator('#plot').hover()
                popup.mouse.wheel(0, 400)
                popup.wait_for_function('() => scrollY > 0')
            popup.screenshot(path=str(directory / 'linked-applet.png'), full_page=True)
            popup.close()
            reports.append('pyhtml: offline iframe and launch link, selected family, fullscreen preserves controls, wheel scroll, one shared runtime')
        if args.only in (None, 'failures'):
            for filename, message in [('no-runtime.html', 'Formeldarstellung'), ('mixed-version.html', 'verschiedenen Versionen')]:
                page.goto((directory / filename).as_uri())
                expect(page.locator('#notice')).to_contain_text(message)
                expect(page.locator('[value="power"]')).to_be_disabled()
            reports.append('failures: missing runtime and stale assets visibly stop startup')
        assert not errors, errors
        print(json.dumps({'passed': reports, 'pageErrors': errors}, ensure_ascii=False, indent=2))
        browser.close()


if __name__ == '__main__':
    main()
