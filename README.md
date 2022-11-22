
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

## Getting started

**NOTE**: For any of the following commands to work, you must first [install Fabric](https://www.fabfile.org/installing.html). Once installed, you can type `fab -l` to see a list of available commands.

**NOTE**: The `.env.example` file contains references to AWS tokens, such as `AWS_ACCESS_KEY_ID`, `AWS_SECRET_KEY` and `AWS_ENDPOINT_URL`. These should only be populated if you are testing locally with `localstack` (though the values do not matter, you can use anything). Leaving them blank will default to your configured AWS account.

### 1. Get access to Marklogic

This app is intended to edit Judgments in the Marklogic database defined in [ds-caselaw-public-access-service/marklogic](https://github.com/nationalarchives/ds-caselaw-public-access-service/tree/main/marklogic).

Unless you are intending to do any database/Marklogic development work, it is simpler to access a
shared Marklogic database running on the `staging` environment than to build your own.

If you wish to run your own Marklogic instance, you will need to follow the setup instructions for it at
[ds-caselaw-public-access-service/marklogic](https://github.com/nationalarchives/ds-caselaw-public-access-service/tree/main/marklogic).

The **recommended** alternative is to access the shared staging Marklogic database. The way you do this
depends on where you work:

#### dxw developers

You will need to be using the dxw vpn. Retrieve the staging Marklogic credentials from dalmatian (or ask
one of the other developers/ops). Use these to fill MARKLOGIC_HOST, MARKLOGIC_USER and MARKLOGIC_PASSWORD
in your `.env` file (see step 2).

#### TNA/other developers

You will need vpn credentials from the dxw ops team, and the staging Marklogic credentials from one of the
dxw development team. Use these to fill MARKLOGIC_HOST, MARKLOGIC_USER and MARKLOGIC_PASSWORD
in your `.env` file (see step 2).

In both cases, when you run the application, you will be viewing data on staging Marklogic. This
data is also used for testing and occasionally user research, so please exercise caution when creating/
editing content!

### 2. Create `.env`

```console
$ cp .env.example .env
```

### 3. Build Docker containers

```console
$ fab build
```

### 4. Run Marklogic

**Note** If you are using the staging instance of Marklogic, you do not need to
follow this step.

Switch to the location of ds-caselaw-public-access-service/marklogic and run:

```console
$ docker-compose up
```

### 5. Start Docker containers

If you have previously run the ds-caselaw-public-ui app you may need to stop its containers (except Marklogic) before
you can run these.

```console
$ fab start
```

#### Create Docker network

You may need to create a docker network if you are running the docker containers for the first time. If you see an
error message referring to a docker network, run:

``` console
$ docker network create caselaw
```


### 6. Start a shell session with the 'django' container

```console
$ fab sh
```

### 7. Add a django user so you can log in

```console
$ ./manage.py createsuperuser
```

### 8. Run a 'development' web server

```console
$ python manage.py runserver_plus 0.0.0.0:3000
```

### 8. Access the site

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

### Localstack

The button that submits an edited document needs S3 and SNS services
to function (as it copies files across and notifies the enrichment
service that it might have been published).

Start it up by running from the `ds-caselaw-ingester` repo:

`docker-compose up -d`

and then, in this repo:

`script/setup-localstack.sh`

That script will create in localstack a `caselaw-stg-judgment-updated` SNS
topic and `public-` and `private-asset-buckets` for S3.

### Running tests

```console
$ fab test
```

## Using the pre-push hook (optional)

Copy `pre-push.sample` to `.git/hooks/pre-push` to set up the pre-push hook. This will run Python linting and style checks when you push to the repo and alert you to any linting issues that will cause CI to fail. To use this, you will need to install [pre-commit](https://pre-commit.com/) on your development machine, typically using `pip install pre-commit`.

## Front end development

Included in this repository is:

* Webpack and Babel for transpiling JavaScript
* Sass for compiling CSS

### Working with SASS/CSS

* Ensure you have NodeJS & NPM installed.
* Install SASS globally by running `npm install -g sass`.
* To watch and build the site SASS, run `npm run start-sass`
* To modify styles, navigate to the `sass` folder in your editor.

#### Note about the Judgment display CSS

The Judgment display CSS should be the same between both
this application and `ds-caselaw-public-ui`. Ensuring edits to the public UI repository were being
replicated to this repository was tricky as it relied on the developers
remembering to make changes in both places.

Instead, we share the judgment CSS between both apps. `ds-caselaw-public-ui` is the "source of truth".
The CSS is located in that repository at `ds_judgements_public_ui/sass/includes/_judgment_text.scss`.

Any edits made in `ds-caselaw-public-ui` which are then merged to main and included in a
production release, will be reflected in `ds-caselaw-editor-ui` (note that the changes have to be included in
[a release](https://github.com/nationalarchives/ds-caselaw-public-ui/releases) before they are used in the editor).

`_judgment_text.scss` only contains styles for the HTML judgment view. Other CSS styles for the public UI and editor
UI applications are not shared.

When running the application locally, the CSS is retrieved from `ds-caselaw-public-ui` via the local Dockerfile
`compose/local/django/Dockerfile`. The Dockerfile retrieves the latest release tag of `ds-caselaw-public-ui`, uses that
tag to build a URL to `_judgment_text.scss` and downloads the CSS to your local application. If you wish to edit the
judgment CSS, you **MUST** make those edits in `ds-caselaw-public-ui`.

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

To login or signup to the staging application, go to `http://localhost:3000/accounts/login`. From there you will be able to log in to an existing account.

### If the login fails for some reason, try creating a new superuser account to gain access.

1) You need have the Docker EUI container running as well as the VPN.
Then you need to make sure 'Fab' is running properly. In the terminal type: `Fab start` 
2) It should say it's up to date. If not, run the commands `fab build` and `fab run` again.
3) Now you can to set up a new user account to access the EUI.
4) In a new terminal window type: `docker-compose exec django bash'
5) After hitting return, type `python manage.py createsuperuser`
6) This should return a username as 'root'. Leave it as this if you want and hit return.
7) Now enter your email address and press enter.
8) Next it will ask for a password which will be used to log in.
9) You will need to input the password again to confirm it.
10) You have now successufully created a new superuser account.
11) Now try logging in to your local EUI using the new credentials. The username will be 'root' assuming that you didn't change it. 

## Deleting judgments on production

Currently there is no way for the editors to delete a judgment from the production site, if the judgment has been assigned
a neutral citation number. Until this functionality is built into the editor UI, judgments need to be deleted manually.
Editors will create a Trello ticket with the URI of the judgment they need removed from the site.

To do this:
- Log in to the [production XQuery console](http://caselaw-alb-16tn9udgqba77-1339658714.eu-west-2.elb.amazonaws.com:8000/qconsole/)
- Get the [XQuery to delete a judgment from the API Client](https://github.com/nationalarchives/ds-caselaw-custom-api-client/blob/main/src/caselawclient/xquery/delete_judgment.xqy)
  (Often there is a pre-existing tab in the XQuery console with this in)
- Add the URI of the judgment to delete to the script; e.g. `declare variable $uri := '<your URI here>'`. Don't forget
  URIs in Marklogic begin with a slash and end in `.xml`
- Run the script, if it is successful it will return no output

## Deployment

### Staging

The `main` branch is automatically deployed with each commit. The deployed app can be viewed at [https://editor.staging.caselaw.nationalarchives.gov.uk/](https://editor.staging.caselaw.nationalarchives.gov.uk/)

### Production

To deploy to production:

1. Create a [new release](https://github.com/nationalarchives/ds-caselaw-editor-ui/releases).
2. Set the tag and release name to `vX.Y.Z`, following semantic versioning.
3. Publish the release.
4. Automated workflow will then force-push that release to the `production` branch, which will then be deployed to the production environment.
5. If you need to roll back to an earlier version, force-push that version to `production` manually.

The production app is at [https://editor.caselaw.nationalarchives.gov.uk/](https://editor.caselaw.nationalarchives.gov.uk/)
