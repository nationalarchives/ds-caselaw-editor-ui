const path = require("path");

module.exports = {
  mode: "development",
  devtool: false,
  entry: {
    app: "./ds_caselaw_editor_ui/static/js/src/app.js",
    cookie_consent:
      "./ds_caselaw_editor_ui/static/js/cookie_consent/src/ds-cookie-consent.js",
    gtm_script: "./ds_caselaw_editor_ui/static/js/src/gtm_script.js",
  },
  output: {
    filename: "[name].js",
    path: path.resolve(__dirname, "ds_caselaw_editor_ui/static/js/dist"),
  },
  module: {
    rules: [
      {
        test: /\.m?js$/,
        exclude: /(node_modules|bower_components)/,
        use: {
          loader: "babel-loader",
          options: {
            presets: ["@babel/preset-env"],
          },
        },
      },
    ],
  },
};
