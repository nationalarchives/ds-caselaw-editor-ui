
# ds-caselaw-editor-ui

## Local development

This project uses Docker to create a consistent environment for local development.

On macOS and Windows, Docker requires [Docker
Desktop](https://www.docker.com/products/docker-desktop) to be installed. Linux
users should install the Docker engine using their distribution's package
manager or [download a `.deb` or
`.rpm`](https://docs.docker.com/engine/install/)

Once installed, we need to build our containers. We use
[`docker-compose`](https://docs.docker.com/compose/) to orchestrate the
building of the project's containers, one for each each service:

### `django`

Our custom container responsible for running the application. Built from the
official [python 3.9](https://hub.docker.com/_/python/) base image

### `postgres`

The database service built from the official [postgres](https://hub.docker.com/_/postgres/) image

### `marklogic`

A database server built from the official [marklogic](https://hub.docker.com/_/marklogic) image.

## Getting started

**NOTE**: For any of the following commands to work, you must first [install Fabric](https://www.fabfile.org/installing.html). Once installed, you can type `fab -l` to see a list of available commands.

**NOTE**: This app is intended to edit Judgments in the Marklogic database for the app ds-caselaw-public-ui. If you do
not already have this application installed, you will need to follow the setup instructions for it. You will need to
run the Marklogic container *only* (see step 3 in this README).

### 1. Create `.env`

```console
$ cp .env.example .env
```

### 2. Build Docker containers

```console
$ fab build
```

### 3. Run Marklogic

Switch to the location of your ds-caselaw-public-ui app and run:

```console
docker-compose up marklogic
```

### 4. Start Docker containers

If you have previously run the ds-caselaw-public-ui app you may need to stop its containers (except Marklogic) before
you can run these.

```console
$ fab start
```

### 5. Start a shell session with the 'django' container

```console
$ fab sh
```

### 6. Run a 'development' web server

```console
$ python manage.py runserver_plus 0.0.0.0:3000
```

### 9. Access the site

<http://127.0.0.1:3000>

**NOTE**: Compiled CSS is not included and therefore needs to be built initially, and after each git pull.

## Quick start with `fab run`

While it's handy to be able to access the django container via a shell and interact with it directly, sometimes all you
want is to view the site in a web browser. In these cases, you can use:

```console
$ fab run
```

This command takes care of the following:

1. Starting all of the necessary Docker containers
2. Installing any new python dependencies
3. Applying any new database migrations
4. Starting the Django development server

You can then access the site in your browser as usual:

<http://127.0.0.1:3000>

### Available Judgments

- <http://127.0.0.1:3000/ewca/civ/2004/632>
- <http://127.0.0.1:3000/ewca/civ/2004/811>
- <http://127.0.0.1:3000/ewca/civ/2006/392>
- <http://127.0.0.1:3000/ewca/civ/2007/214>

### Running tests

```console
$ fab test
```

## Using the pre-push hook (optional)

Copy `pre-push.sample` to `.git/hooks/pre-push` to set up the pre-push hook. This will run Python linting and style checks when you push to the repo and alert you to any linting issues that will cause CI to fail.

## Front end development

Included in this repository is:

* Webpack and Babel for transpiling JavaScript
* Sass for compiling CSS

### Working with SASS/CSS

* Ensure you have NodeJS & NPM installed.
* Install SASS globally by running `npm install -g sass`.
* To watch and build the site SASS, run `npm run start-sass`
* To modify styles, navigate to the `sass` folder in your editor.

### Working with JavaScript

* In a new terminal session run `npm run start-scripts` to kick off a Webpack watch task

### Internationalisation

We're using [the built-in django translation module](https://docs.djangoproject.com/en/4.0/topics/i18n/translation) to handle our translations.

#### Adding translations

1) Ensure that the `i18n` module is loaded at the top of the file:

```django
{% extends 'base.html' %}
{% load i18n %}
...
```

2) Add the translation string to the page:
```
<h1>{% translate "namespace.mytranslation" %}</h1>
```

3) Update the locale file by running the following command:
```
django-admin makemessages -l {langage_code}
```

where `language_code` is the ISO 3166-1 country code (e.g. en_GB)

4) In the generated `.po` file, find the generated msgid string and add the translation below it

```
msgid "naamespace.mytranslation"
msgstr "This is my translation"
```

5) Compile the translations to a binary file:
```
django-admin compilemessages
```

## Authentication

To login or signup to the staging application, go to `http://localhost:3000/accounts/login`. From there you will be able to create an account or login to an existing one.

Authentication is provided by [Auth0](https://auth0.com).
