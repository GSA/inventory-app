
// ***********************************************************
// This example plugins/index.js can be used to load plugins
//
// You can change the location of this file or turn off loading
// the plugins file with the 'pluginsFile' configuration option.
//
// You can read more here:
// https://on.cypress.io/plugins-guide
// ***********************************************************

// This function is called when a project is opened or re-opened (e.g. due to
// the project's config changing)

// module.exports = (on, config) => {
//     // `on` is used to hook into various events Cypress emits
//     // `config` is the resolved Cypress config
// }

const path = require('path');
const fs = require('fs');

const downloadDirectory = path.join(__dirname, '..', 'downloads');

const findDownload = (fileName) => {
    const filePath = `${downloadDirectory}/${fileName}`;
    const file_exists = fs.existsSync(filePath);
    console.log()
    return (file_exists ? filePath : false);
};

const hasFile = (fileName, ms) => {
    const delay = 10;
    return new Promise((resolve, reject) => {
    if (ms < 0) {
        return reject(
        new Error(`Could not find file ${downloadDirectory}/${fileName}`)
        );
    }
    const found = findDownload(fileName);
    if (found) {
        console.log('Found file! ' + found)
        return resolve(fs.readFileSync(found).toString());
    }
    setTimeout(() => {
        hasFile(fileName, ms - delay).then(resolve, reject);
    }, 10);
    });
};

module.exports = (on, config) => {
    // require('@cypress/code-coverage/task')(on, config);
    // on('before:browser:launch', (browser, options) => {
    // if (browser.family === 'chromium') {
    //     options.preferences.default['download'] = {
    //     default_directory: downloadDirectory,
    //     };
    //     return options;
    // }
    // if (browser.family === 'firefox') {
    //     options.preferences['browser.download.dir'] = downloadDirectory;
    //     options.preferences['browser.download.folderList'] = 2;
    //     options.preferences['browser.helperApps.neverAsk.saveToDisk'] =
    //     'text/csv';
    //     return options;
    // }
    // });

    on('task', {
    isExistFile(fileName, ms = 4000) {
        console.log(
        `looking for file in ${downloadDirectory}`,
        fileName,
        ms
        );
        return hasFile(fileName, ms);
    }
    });

    return config;
};