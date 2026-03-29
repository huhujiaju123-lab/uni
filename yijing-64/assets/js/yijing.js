/* ============================================================
   易经64卦 — 统一交互系统
   ============================================================ */

(function() {
  'use strict';

  // --- Scroll-triggered fade-in ---
  var fadeObserver = new IntersectionObserver(function(entries) {
    entries.forEach(function(entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        fadeObserver.unobserve(entry.target);
      }
    });
  }, { rootMargin: '0px 0px -60px 0px', threshold: 0.1 });

  document.querySelectorAll('.fade-in').forEach(function(el) {
    fadeObserver.observe(el);
  });

  // --- Sticky Navigation ---
  var mainNav = document.querySelector('.nav');
  var lastScrollTop = 0;
  var heroHeight = 0;
  var heroEl = document.querySelector('.hero');
  if (heroEl) {
    heroHeight = heroEl.offsetHeight;
  }

  window.addEventListener('scroll', function() {
    var scrollTop = window.scrollY;

    // Show nav after passing hero
    if (scrollTop > heroHeight * 0.8) {
      if (scrollTop < lastScrollTop) {
        mainNav && mainNav.classList.add('visible');
      } else {
        mainNav && mainNav.classList.remove('visible');
      }
    } else {
      mainNav && mainNav.classList.remove('visible');
    }

    lastScrollTop = scrollTop;

    // Update active nav link
    updateActiveNavLink();

    // Back to top visibility
    var backToTop = document.querySelector('.back-to-top');
    if (backToTop) {
      if (scrollTop > 300) {
        backToTop.classList.add('visible');
      } else {
        backToTop.classList.remove('visible');
      }
    }
  });

  // --- Active Nav Link Tracking ---
  function updateActiveNavLink() {
    var sections = document.querySelectorAll('section[id]');
    var navLinks = document.querySelectorAll('.nav-links a');
    var scrollPos = window.scrollY + 100;

    sections.forEach(function(section) {
      var top = section.offsetTop;
      var height = section.offsetHeight;
      var id = section.getAttribute('id');

      if (scrollPos >= top && scrollPos < top + height) {
        navLinks.forEach(function(link) {
          link.classList.remove('active');
          if (link.getAttribute('href') === '#' + id) {
            link.classList.add('active');
          }
        });
      }
    });
  }

  // --- Back to Top ---
  var backToTopBtn = document.querySelector('.back-to-top');
  if (backToTopBtn) {
    backToTopBtn.addEventListener('click', function() {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  // --- Chart Animation ---
  var chartAnimated = false;
  var chartContainer = document.querySelector('.chart-container');

  if (chartContainer) {
    var chartObserver = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) {
        if (entry.isIntersecting && !chartAnimated) {
          chartAnimated = true;
          animateChart();
        }
      });
    }, { threshold: 0.3 });

    chartObserver.observe(chartContainer);
  }

  function animateChart() {
    // Animate SVG paths
    var paths = document.querySelectorAll('.chart-path');
    paths.forEach(function(path) {
      if (path.getTotalLength) {
        var length = path.getTotalLength();
        path.style.strokeDasharray = length;
        path.style.strokeDashoffset = length;
        requestAnimationFrame(function() {
          path.classList.add('animated');
          path.style.strokeDashoffset = '0';
        });
      }
    });

    // Animate dots with stagger
    var dots = document.querySelectorAll('.chart-dot');
    dots.forEach(function(dot, i) {
      setTimeout(function() {
        dot.classList.add('animated');
      }, 300 + i * 200);
    });
  }

  // --- Chart Tooltip ---
  var tooltip = document.querySelector('.chart-tooltip');
  if (tooltip) {
    var dots = document.querySelectorAll('.chart-dot[data-label]');
    dots.forEach(function(dot) {
      dot.addEventListener('mouseenter', function(e) {
        var label = this.getAttribute('data-label');
        var desc = this.getAttribute('data-desc') || '';
        tooltip.innerHTML = '<strong>' + label + '</strong>' + (desc ? '<br/>' + desc : '');
        tooltip.style.opacity = '1';

        var rect = chartContainer.getBoundingClientRect();
        var cx = parseFloat(this.getAttribute('cx') || this.getBBox().x);
        var cy = parseFloat(this.getAttribute('cy') || this.getBBox().y);
        tooltip.style.left = cx + 'px';
        tooltip.style.top = (cy - 50) + 'px';
      });

      dot.addEventListener('mouseleave', function() {
        tooltip.style.opacity = '0';
      });
    });
  }

  // --- Smooth scroll for nav links ---
  document.querySelectorAll('.nav-links a, a[href^="#"]').forEach(function(link) {
    link.addEventListener('click', function(e) {
      var href = this.getAttribute('href');
      if (href && href.startsWith('#')) {
        e.preventDefault();
        var target = document.querySelector(href);
        if (target) {
          var offset = 60; // nav height
          var top = target.getBoundingClientRect().top + window.scrollY - offset;
          window.scrollTo({ top: top, behavior: 'smooth' });
        }
      }
    });
  });

})();
