const express = require('express');
const os      = require('os');
const router  = express.Router();

/**
 * GET /api/health
 * Returns service status, uptime, memory, and model connection info.
 */
router.get('/', (req, res) => {
  const mem    = process.memoryUsage();
  const uptime = process.uptime();

  res.json({
    status:    'ok',
    service:   'BundleIQ Insurance Recommender API',
    version:   '1.0.0',
    timestamp: new Date().toISOString(),
    uptime: {
      seconds: Math.floor(uptime),
      human:   formatUptime(uptime),
    },
    memory: {
      heapUsed:  fmt(mem.heapUsed),
      heapTotal: fmt(mem.heapTotal),
      rss:       fmt(mem.rss),
    },
    system: {
      platform:   os.platform(),
      cpus:       os.cpus().length,
      freeMemory: fmt(os.freemem()),
    },
    model: {
      status:   process.env.PYTHON_API_URL ? 'connected' : 'demo_mode',
      endpoint: process.env.PYTHON_API_URL || 'mock (no PYTHON_API_URL set)',
    },
  });
});

const fmt         = (b) => `${(b / 1024 / 1024).toFixed(1)} MB`;
const formatUptime = (s) => {
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = Math.floor(s % 60);
  return `${h}h ${m}m ${sec}s`;
};

module.exports = router;
