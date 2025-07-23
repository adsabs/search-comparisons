const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  app.use(
    '/api',
    createProxyMiddleware({
      target: 'http://127.0.0.1:8001/api',
      changeOrigin: true,
      pathRewrite: {
        '^/api': '', // Remove /api from path since target already includes it
      },
    })
  );
};
