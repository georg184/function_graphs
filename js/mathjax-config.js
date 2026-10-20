'use strict';

window.MathJax = {
  loader: {
    paths: {
      sre: 'data:application/javascript,void%200#',
      mathmaps: 'data:application/json,%7B%7D#'
    }
  },
  startup: {
    pageReady: () => {
      const fontsReady = document.fonts?.ready ?? Promise.resolve();
      return fontsReady.then(() => MathJax.startup.defaultPageReady());
    }
  },
  tex: {
    packages: { '[-]': ['autoload', 'require'] },
    inlineMath: [['\\(', '\\)']],
    displayMath: [['\\[', '\\]']],
    processEscapes: true,
    tags: 'none'
  },
  options: {
    enableMenu: false,
    enableEnrichment: false,
    enableComplexity: false,
    enableSpeech: false,
    enableBraille: false,
    enableExplorer: false,
    // Combined MathJax components also enable accessibility through menu settings.
    menuOptions: {
      settings: {
        enrich: false,
        collapsible: false,
        speech: false,
        braille: false,
        assistiveMml: false
      }
    },
    a11y: {
      speech: false,
      braille: false,
      subtitles: false,
      viewBraille: false,
      voicing: false
    },
    renderActions: {
      addMenu: [],
      enrich: [],
      attachSpeech: [],
      complexity: [],
      explorable: []
    }
  },
  output: {
    font: 'mathjax-modern',
    mtextInheritFont: true,
    linebreaks: {
      inline: false
    }
  },
  svg: {
    fontCache: 'local'
  }
};
