# Authors:
#   Jason Gerard DeRose <jderose@redhat.com>
#
# Copyright (C) 2008  Red Hat
# see file 'COPYING' for use and warranty information
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; version 2 only
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA


'''
Package containing the core library.

=============================
 Tutorial for Plugin Authors
=============================

This tutorial will introduce you to writing plugins for freeIPA v2. It does
not cover every detail, but it provides enough to get you started and is
heavily cross-referenced with further documentation that (hopefully) fills
in the missing details.

In addition to this tutorial, the many built-in plugins in `ipalib.plugins`
and `ipa_server.plugins` provide real-life examples of how to write good
plugins.


----------------------------
How this tutorial is written
----------------------------

The code examples in this tutorial are presented as if entered into a Python
interactive interpreter session.  As such, when you create a real plugin in
a source file, a few details will be different (in addition to the fact that
you will never include the ``>>>`` nor ``...`` that the interpreter places at
the beginning of each line of code).

The tutorial examples all have this pattern:

    ::

        >>> from ipalib import Command, create_api
        >>> api = create_api()
        >>> class my_command(Command):
        ...     pass
        ...
        >>> api.register(my_command)
        >>> api.finalize()

In the tutorial we call `create_api()` to create an *example* instance
of `plugable.API` to work with.  But a real plugin will simply use
``ipalib.api``, the standard run-time instance of `plugable.API`.

A real plugin will have this pattern:

    ::

        from ipalib import Command, api

        class my_command(Command):
            pass
        api.register(my_command)

As seen above, also note that in a real plugin you will *not* call
`plugable.API.finalize()`.  When in doubt, look at some of the built-in
plugins for guidance, like those in `ipalib.plugins`.

If you don't know what the Python *interactive interpreter* is, or are
confused about what this *Python* is in the first place, then you probably
should start with the Python tutorial:

    http://docs.python.org/tutorial/index.html


------------------------------------
First steps: A simple command plugin
------------------------------------

Our first example will create the most basic command plugin possible.  This
command will be seen in the list of command plugins, but it wont be capable
of actually doing anything yet.

A command plugin simultaneously adds a new command that can be called through
the command-line ``ipa`` script *and* adds a new XML-RPC method... the two are
one in the same, simply invoked in different ways.

A freeIPA plugin is a Python class, and when you create a plugin, you register
this class itself (instead of an instance of the class).  To be a command
plugin, your plugin must subclass from `frontend.Command` (or from a subclass
thereof).  Here is our first example:

>>> from ipalib import Command, create_api
>>> api = create_api()
>>> class my_command(Command): # Step 1, define class
...     """My example plugin."""
...
>>> api.register(my_command) # Step 2, register class

Notice that we are registering the ``my_command`` class itself, not an
instance of ``my_command``.

Until `plugable.API.finalize()` is called, your plugin class has not been
instantiated nor does the ``Command`` namespace yet exist.  For example:

>>> hasattr(api, 'Command')
False
>>> api.finalize() # plugable.API.finalize()
>>> hasattr(api.Command, 'my_command')
True
>>> api.Command.my_command.doc
'My example plugin.'

Notice that your plugin instance is accessed through an attribute named
``my_command``, the same name as your plugin class name.


------------------------------
Make your command do something
------------------------------

This simplest way to make your example command plugin do something is to
implement a ``run()`` method, like this:

>>> class my_command(Command):
...     """My example plugin with run()."""
...
...     def run(self):
...         return 'My run() method was called!'
...
>>> api = create_api()
>>> api.register(my_command)
>>> api.finalize()
>>> api.Command.my_command() # Call your command
'My run() method was called!'

When `frontend.Command.__call__()` is called, it first validates any arguments
and options your command plugin takes (if any) and then calls its ``run()``
method.


------------------------
Forwarding vs. execution
------------------------

However, unlike the example above, a typical command plugin will implement an
``execute()`` method instead of a ``run()`` method.  Your command plugin can
be loaded in two distinct contexts:

    1. In a *client* context - Your command plugin is only used to validate
       any arguments and options it takes, and then ``self.forward()`` is
       called, which forwards the call over XML-RPC to an IPA server where
       the actual work is done.

    2. In a *server* context - Your same command plugin validates any
       arguments and options it takes, and then ``self.execute()`` is called,
       which you should implement to perform whatever work your plugin does.

The base `frontend.Command.run()` method simply dispatches the call to
``self.execute()`` if ``self.env.in_server`` is True, or otherwise
dispatches the call to ``self.forward()``.

For example, say you have a command plugin like this:

>>> class my_command(Command):
...     """Forwarding vs. execution."""
...
...     def forward(self):
...         return 'in_server=%r; forward() was called.' % self.env.in_server
...
...     def execute(self):
...         return 'in_server=%r; execute() was called.' % self.env.in_server
...

If ``my_command`` is loaded in a *client* context, ``forward()`` will be
called:

>>> api = create_api()
>>> api.env.in_server = False # run() will dispatch to forward()
>>> api.register(my_command)
>>> api.finalize()
>>> api.Command.my_command() # Call your command plugin
'in_server=False; forward() was called.'

On the other hand, if ``my_command`` is loaded in a *server* context,
``execute()`` will be called:

>>> api = create_api()
>>> api.env.in_server = True # run() will dispatch to execute()
>>> api.register(my_command)
>>> api.finalize()
>>> api.Command.my_command() # Call your command plugin
'in_server=True; execute() was called.'

Normally there should be no reason to override `frontend.Command.forward()`,
but, as above, it can be done for demonstration purposes.  In contrast, there
*is* a reason you might want to override `frontend.Command.run()`: if it only
makes sense to execute your command locally, if it should never be forwarded
to the server.  In this case, you should implement your *do-stuff* in the
``run()`` method instead of in the ``execute()`` method.

For example, the ``ipa`` command line script has a ``help`` command
(`ipalib.cli.help`) that is specific to the command-line-interface and should
never be forwarded to the server.


---------------
Backend plugins
---------------

There are two types of plugins:

    1. *Frontend plugins* - These are loaded in both the *client* and *server*
       contexts.  These need to be installed with any application built atop
       the `ipalib` library.  The built-in frontend plugins can be found in
       `ipalib.plugins`.  The ``my_command`` example above is a frontend
       plugin.

    2. *Backend plugins* - These are only loaded in a *server* context and
       only need to be installed on the IPA server.  The built-in backend
       plugins can be found in `ipa_server.plugins`.

Backend plugins should provide a set of methods that standardize how IPA
interacts with some external system or library.  For example, all interaction
with LDAP is done through the ``ldap`` backend plugin defined in
`ipa_server.plugins.b_ldap`.  As a good rule of thumb, anytime you need to
import some package that is not part of the Python standard library, you
should probably interact with that package via a corresponding backend
plugin you implement.

Backend plugins are much more free-form than command plugins.  Aside from a
few reserved attribute names, you can define arbitrary public methods on your
backend plugin (in contrast, frontend plugins get wrapped in a
`plugable.PluginProxy`, which allow access to only specific attributes on the
frontend plugin).

Here is a simple example:

>>> from ipalib import Backend
>>> class my_backend(Backend):
...     """My example backend plugin."""
...
...     def do_stuff(self):
...         """Part of your API."""
...         return 'Stuff got done.'
...
>>> api = create_api()
>>> api.register(my_backend)
>>> api.finalize()
>>> api.Backend.my_backend.do_stuff()
'Stuff got done.'


-------------------------------
How your command should do work
-------------------------------

We now return to our ``my_command`` plugin example.

Plugins are separated into frontend and backend plugins so that there are not
unnecessary dependencies required by an application that only uses `ipalib` and
its built-in frontend plugins (and then forwards over XML-RPC for execution).

But how do we avoid introducing additional dependencies?  For example, the
``user_add`` command needs to talk to LDAP to add the user, yet we want to
somehow load the ``user_add`` plugin on client machines without requiring the
``python-ldap`` package (Python bindings to openldap) to be installed.  To
answer that, we consult our golden rule:

  **The golden rule:** A command plugin should implement its ``execute()``
  method strictly via calls to methods on one or more backend plugins.

So the module containing the ``user_add`` command does not itself import the
Python LDAP bindings, only the module containing the ``ldap`` backend plugin
does that, and the backend plugins are only installed on the server.  The
``user_add.execute()`` method, which is only called when in a server context,
is implemented as a series of calls to methods on the ``ldap`` backend plugin.

When `plugable.Plugin.set_api()` is called, each plugin stores a reference to
the `plugable.API` instance it has been loaded into.  So your plugin can
access the ``my_backend`` plugin as ``self.api.Backend.my_backend``.

Additionally, convenience attributes are set for each namespace, so your
plugin can also access the ``my_backend`` plugin as simply
``self.Backend.my_backend``.

This next example will tie everything together.  First we create our backend
plugin:

>>> api = create_api()
>>> api.env.in_server = True # We want to execute, not forward
>>> class my_backend(Backend):
...     """My example backend plugin."""
...
...     def do_stuff(self):
...         """my_command.execute() calls this."""
...         return 'my_backend.do_stuff() indeed did do stuff!'
...
>>> api.register(my_backend)

Second, we have our frontend plugin, the command:

>>> class my_command(Command):
...     """My example command plugin."""
...
...     def execute(self):
...         """Implemented against Backend.my_backend"""
...         return self.Backend.my_backend.do_stuff()
...
>>> api.register(my_command)

Lastly, we call ``api.finalize()`` and see what happens when we call
``my_command()``:

>>> api.finalize()
>>> api.Command.my_command()
'my_backend.do_stuff() indeed did do stuff!'

When not in a server context, ``my_command.execute()`` never gets called, so
it never tries to access the non-existent backend plugin at
``self.Backend.my_backend.``  To emphasize this point, here is one last
example:

>>> api = create_api()
>>> api.env.in_server = False # We want to forward, not execute
>>> class my_command(Command):
...     """My example command plugin."""
...
...     def execute(self):
...         """Same as above."""
...         return self.Backend.my_backend.do_stuff()
...
...     def forward(self):
...         return 'Just my_command.forward() getting called here.'
...
>>> api.register(my_command)
>>> api.finalize()

Notice that the ``my_backend`` plugin has certainly not be registered:

>>> hasattr(api.Backend, 'my_backend')
False

And yet we can call ``my_command()``:

>>> api.Command.my_command()
'Just my_command.forward() getting called here.'


----------------------------------------
Calling other commands from your command
----------------------------------------

It can be useful to have your ``execute()`` method call other command plugins.
Among other things, this allows for meta-commands that conveniently call
several other commands in a single operation.  For example:

>>> api = create_api()
>>> api.env.in_server = True # We want to execute, not forward
>>> class meta_command(Command):
...     """My meta-command plugin."""
...
...     def execute(self):
...         """Calls command_1(), command_2()"""
...         return '%s; %s.' % (
...             self.Command.command_1(),
...             self.Command.command_2()
...         )
>>> class command_1(Command):
...     def execute(self):
...         return 'command_1.execute() called'
...
>>> class command_2(Command):
...     def execute(self):
...         return 'command_2.execute() called'
...
>>> api.register(meta_command)
>>> api.register(command_1)
>>> api.register(command_2)
>>> api.finalize()
>>> api.Command.meta_command()
'command_1.execute() called; command_2.execute() called.'

Because this is quite useful, we are going to revise our golden rule somewhat:

  **The revised golden rule:** A command plugin should implement its
  ``execute()`` method strictly via what it can access through ``self.api``,
  most likely via the backend plugins in ``self.api.Backend`` (which can also
  be conveniently accessed as ``self.Backend``).


-----------------------------------------------
Defining arguments and options for your command
-----------------------------------------------

You can define a command that will accept specific arguments and options.
For example:

>>> from ipalib import Param
>>> class nudge(Command):
...     """Takes one argument, one option"""
...
...     takes_args = ['programmer']
...
...     takes_options = [Param('stuff', default=u'documentation')]
...
...     def execute(self, programmer, **kw):
...         return '%s, go write more %s!' % (programmer, kw['stuff'])
...
>>> api = create_api()
>>> api.env.in_server = True
>>> api.register(nudge)
>>> api.finalize()
>>> api.Command.nudge('Jason')
u'Jason, go write more documentation!'
>>> api.Command.nudge('Jason', stuff='unit tests')
u'Jason, go write more unit tests!'

The ``args`` and ``options`` attributes are `plugable.NameSpace` instances
containing a command's arguments and options, respectively, as you can see:

>>> list(api.Command.nudge.args) # Iterates through argument names
['programmer']
>>> api.Command.nudge.args.programmer
Param('programmer')
>>> list(api.Command.nudge.options) # Iterates through option names
['stuff']
>>> api.Command.nudge.options.stuff
Param('stuff', default=u'documentation')
>>> api.Command.nudge.options.stuff.default
u'documentation'

The arguments and options must not contain colliding names.  They are both
merged together into the ``params`` attribute, another `plugable.NameSpace`
instance, as you can see:

>>> api.Command.nudge.params
NameSpace(<2 members>, sort=False)
>>> list(api.Command.nudge.params) # Iterates through the param names
['programmer', 'stuff']

When calling a command, its positional arguments can also be provided as
keyword arguments, and in any order.  For example:

>>> api.Command.nudge(stuff='lines of code', programmer='Jason')
u'Jason, go write more lines of code!'

When a command plugin is called, the values supplied for its parameters are
put through a sophisticated processing pipeline that includes steps for
normalization, type conversion, validation, and dynamically constructing
the defaults for missing values.  The details wont be covered here; however,
here is a quick teaser:

>>> from ipalib import Int
>>> class create_player(Command):
...     takes_options = [
...         'first',
...         'last',
...         Param('nick',
...             normalize=lambda value: value.lower(),
...             default_from=lambda first, last: first[0] + last,
...         ),
...         Param('points', type=Int(), default=0),
...     ]
...
>>> cp = create_player()
>>> cp.finalize()
>>> cp.convert(points=" 1000  ")
{'points': 1000}
>>> cp.normalize(nick=u'NickName')
{'nick': u'nickname'}
>>> cp.get_default(first='Jason', last='DeRose')
{'nick': u'jderose', 'points': 0}

For the full details on the parameter system, see the
`frontend.parse_param_spec()` function, and the `frontend.Param` and
`frontend.Command` classes.


---------------------------------------
Allowed return values from your command
---------------------------------------

The return values from your command can be rendered by different user
interfaces (CLI, web-UI); furthermore, a call to your command can be
transparently forwarded over the network (XML-RPC, JSON).  As such, the return
values from your command must be usable by the least common denominator.

Your command should return only simple data types and simple data structures,
the kinds that can be represented in an XML-RPC request or in the JSON format.
The return values from your command's ``execute()`` method can include only
the following:

    Simple scalar values:
        These can be ``str``, ``unicode``, ``int``, and ``float`` instances,
        plus the ``True``, ``False``, and ``None`` constants.

    Simple compound values:
        These can be ``dict``, ``list``, and ``tuple`` instances.  These
        compound values must contain only the simple scalar values above or
        other simple compound values.  These compound values can also be empty.
        For our purposes here, the ``list`` and ``tuple`` types are equivalent
        and can be used interchangeably.

Also note that your ``execute()`` method should not contain any ``print``
statements or otherwise cause any output on ``sys.stdout``.  Your command can
(and should) produce log messages by using ``self.log`` (see below).

To learn more about XML-RPC (XML Remote Procedure Call), see:

    http://docs.python.org/library/xmlrpclib.html

    http://en.wikipedia.org/wiki/XML-RPC

To learn more about JSON (Java Script Object Notation), see:

    http://docs.python.org/library/json.html

    http://www.json.org/


---------------------------------------
How your command should print to stdout
---------------------------------------

As noted above, your command should not print anything while in its
``execute()`` method.  So how does your command format its output when
called from the ``ipa`` script?

After the `cli.CLI.run_cmd()` method calls your command, it will call your
command's ``output_for_cli()`` method (if you have implemented one).

If you implement an ``output_for_cli()`` method, it must have the following
signature:

    ::

        output_for_cli(textui, result, *args, **options)

    textui
        An object implementing methods for outputting to the console.
        Currently the `ipalib.cli.textui` plugin is passed, which your method
        can also access as ``self.Backend.textui``.  However, in case this
        changes in the future, your method should use the instance passed to
        it in this first argument.

    result
        This is the return value from calling your command plugin.  Depending
        upon how your command is implemented, this is probably the return
        value from your ``execute()`` method.

    args
        The arguments your command was called with.  If your command takes no
        arguments, you can omit this.  You can also explicitly list your
        arguments rather than using the generic ``*args`` form.

    options
        The options your command was called with.  If your command takes no
        options, you can omit this.  If your command takes any options, you
        must use the ``**options`` form as they will be provided strictly as
        keyword arguments.

For example, say we setup a command like this:

>>> class show_items(Command):
...
...     takes_args = ['key?']
...
...     takes_options = [Param('reverse', type=Bool(), default=False)]
...
...     def execute(self, key, **options):
...         items = dict(
...             fruit='apple',
...             pet='dog',
...             city='Berlin',
...         )
...         if key in items:
...             return items[key]
...         return [
...             (k, items[k]) for k in sorted(items, reverse=options['reverse'])
...         ]
...
...     def output_for_cli(self, textui, result, key, **options):
...         if key is not None:
...             textui.print_plain('%s = %r' % (key, result))
...         else:
...             textui.print_name(self.name)
...             textui.print_keyval(result)
...             format = '%d items'
...             if options['reverse']:
...                 format += ' (in reverse order)'
...             textui.print_count(result, format)
...
>>> api = create_api()
>>> api.env.in_server = True  # We want to execute, not forward.
>>> api.register(show_items)
>>> api.finalize()

Normally when you invoke the ``ipa`` script, `cli.CLI.load_plugins()` will
register the `cli.textui` backend plugin, but for the sake of our example,
we  just create an instance here:

>>> from ipalib import cli
>>> textui = cli.textui()  # We'll pass this to output_for_cli()

Now for what we are concerned with in this example, calling your command
through the ``ipa`` script basically will do the following:

>>> result = api.Command.show_items()
>>> api.Command.show_items.output_for_cli(textui, result, None, reverse=False)
-----------
show-items:
-----------
  city = 'Berlin'
  fruit = 'apple'
  pet = 'dog'
-------
3 items
-------

Similarly, calling it with ``reverse=True``  would result in the following:

>>> result = api.Command.show_items(reverse=True)
>>> api.Command.show_items.output_for_cli(textui, result, None, reverse=True)
-----------
show-items:
-----------
  pet = 'dog'
  fruit = 'apple'
  city = 'Berlin'
--------------------------
3 items (in reverse order)
--------------------------

Lastly, providing a ``key`` would result in the following:

>>> result = api.Command.show_items('city')
>>> api.Command.show_items.output_for_cli(textui, result, 'city', reverse=False)
city = 'Berlin'

See the `ipalib.cli.textui` plugin for a description of its methods.


------------------------
Logging from your plugin
------------------------

After `plugable.Plugin.set_api()` is called, your plugin will have a
``self.log`` attribute.  Plugins should only log through this attribute.
For example:

>>> class paint_house(Command):
...
...     takes_args = ['color']
...
...     def execute(self, color):
...         """Uses self.log.error()"""
...         if color not in ('red', 'blue', 'green'):
...             self.log.error("I don't have %s paint!", color) # Log error
...             return
...         return 'I painted the house %s.' % color
...

Some basic knowledge of the Python ``logging`` module might be helpful. See:

    http://docs.python.org/library/logging.html

The important thing to remember is that your plugin should not configure
logging itself, but should instead simply use the ``self.log`` logger.

Also see the `plugable.API.bootstrap()` method for details on how the logging
is configured.


---------------------
Environment variables
---------------------

Plugins access various environment variables and run-time information through
``self.api.env`` (for convenience, ``self.env`` is equivalent).

When you create a fresh `plugable.API` instance, its ``env`` attribute is
likewise a freshly created `config.Env` instance, which will already be
populated with certain run-time information.  For example:

>>> api = create_api()
>>> list(api.env)
['bin', 'dot_ipa', 'home', 'ipalib', 'mode', 'script', 'site_packages']

Here is a quick overview of the run-time information:

=============  ================================  =======================
Key            Source or example value           Description
=============  ================================  =======================
bin            /usr/bin                          Dir. containing script
dot_ipa        ~/.ipa                            User config directory
home           os.environ['HOME']                User home dir.
ipalib         .../site-packages/ipalib          Dir. of ipalib package
mode           'production' or 'unit_test'       The mode ipalib is in
script         sys.argv[0]                       Path of script
site_packages  /usr/lib/python2.5/site-packages  Dir. containing ipalib/
=============  ================================  =======================

After `plugable.API.bootstrap()` has been called, the env instance will be
populated with all the environment information used by the built-in plugins.
This will typically be called before any plugins are registered.  For example:

>>> len(api.env)
7
>>> api.bootstrap(in_server=True) # We want to execute, not forward
>>> len(api.env)
34

If your plugin requires new environment variables *and* will be included in
the freeIPA built-in plugins, you should add the defaults for your variables
in `ipalib.constants.DEFAULT_CONFIG`.  Also, you should consider whether your
new environment variables should have any auto-magic logic to determine their
values if they haven't already been set by the time `config.Env._bootstrap()`,
`config.Env._finalize_core()`, or `config.Env._finalize()` is called.

On the other hand, if your plugin requires new environment variables and will
be installed in a 3rd-party package, your plugin should set these variables
in the module it is defined in.

`config.Env` values work on a first-one-wins basis... after a value has been
set, it can not be overridden with a new value.  As any variables can be set
using the command-line ``-e`` global option or set in a configuration file,
your module must check whether a variable has already been set before
setting its default value.  For example:

>>> if 'message_of_the_day' not in api.env:
...     api.env.message_of_the_day = 'Hello, world!'
...

Your plugin can access any environment variables via ``self.env``.
For example:

>>> class motd(Command):
...     """Print message of the day."""
...
...     def execute(self):
...         return self.env.message_of_the_day
...
>>> api.register(motd)
>>> api.finalize()
>>> api.Command.motd()
'Hello, world!'

Also see the `plugable.API.bootstrap_with_global_options()` method.


---------------------------------------------
Indispensable ipa script commands and options
---------------------------------------------

The ``console`` command will launch a custom interactive Python interpreter
session.  The global environment will have an ``api`` variable, which is the
standard `plugable.API` instance found at ``ipalib.api``.  All plugins will
have been loaded (well, except the backend plugins if ``in_server`` is False)
and ``api`` will be fully initialized.  To launch the console from within the
top-level directory in the the source tree, just run ``ipa console`` from a
terminal, like this:

    ::

        $ ./ipa console

By default, ``in_server`` is False.  If you want to start the console in a
server context (so that all the backend plugins are loaded), you can use the
``-e`` option to set the ``in_server`` environment variable, like this:

    ::

        $ ./ipa -e in_server=True console

You can specify multiple environment variables by including the ``-e`` option
multiple times, like this:

    ::

        $ ./ipa -e in_server=True -e mode=dummy console

The space after the ``-e`` is optional.  This is equivalent to the above command:

    ::

        $ ./ipa -ein_server=True -emode=dummy console

The ``env`` command will print out the full environment in key=value pairs,
like this:

    ::

        $ ./ipa env

If you use the ``--server`` option, it will forward the call to the server
over XML-RPC and print out what the environment is on the server, like this:

    ::

        $ ./ipa env --server

The ``plugins`` command will show details of all the plugin that are loaded,
like this:

    ::

        $ ./ipa plugins


-----------------------------------
Learning more about freeIPA plugins
-----------------------------------

To learn more about writing freeIPA plugins, you should:

    1. Look at some of the built-in plugins, like the frontend plugins in
       `ipalib.plugins.f_user` and the backend plugins in
       `ipa_server.plugins.b_ldap`.

    2. Learn about the base classes for frontend plugins in `ipalib.frontend`.

    3. Learn about the core plugin framework in `ipalib.plugable`.

Furthermore, the freeIPA plugin architecture was inspired by the Bazaar plugin
architecture.  Although the two are different enough that learning how to
write plugins for Bazaar will not particularly help you write plugins for
freeIPA, some might be interested in the documentation on writing plugins for
Bazaar, available here:

    http://bazaar-vcs.org/WritingPlugins

If nothing else, we just want to give credit where credit is deserved!
However, freeIPA does not use any *code* from Bazaar... it merely borrows a
little inspiration.


--------------------------
A note on docstring markup
--------------------------

Lastly, a quick note on markup:  All the Python docstrings in freeIPA v2
(including this tutorial) use the *reStructuredText* markup language.  For
information on reStructuredText, see:

    http://docutils.sourceforge.net/rst.html

For information on using reStructuredText markup with epydoc, see:

    http://epydoc.sourceforge.net/manual-othermarkup.html


--------------------------------------------------
Next steps: get involved with freeIPA development!
--------------------------------------------------

The freeIPA team is always interested in feedback and contribution from the
community.  To get involved with freeIPA, see the *Contribute* page on
freeIPA.org:

    http://freeipa.org/page/Contribute

'''

import plugable
from backend import Backend, Context
from frontend import Command, Object, Method, Property, Application
from ipa_types import Bool, Int, Unicode, Enum
from frontend import Param, DefaultFrom

def create_api(mode='dummy'):
    """
    Return standard `plugable.API` instance.

    This standard instance allows plugins that subclass from the following
    base classes:

        - `frontend.Command`

        - `frontend.Object`

        - `frontend.Method`

        - `frontend.Property`

        - `frontend.Application`

        - `backend.Backend`

        - `backend.Context`
    """
    api = plugable.API(
        Command, Object, Method, Property, Application,
        Backend, Context,
    )
    if mode is not None:
        api.env.mode = mode
    return api


api = create_api(mode=None)
