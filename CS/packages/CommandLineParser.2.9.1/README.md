[![Build status](https://ci.appveyor.com/api/projects/status/p61dj8udxs2aocmo/branch/master?svg=true)](https://ci.appveyor.com/project/commandlineparser/commandline/branch/master)
[![NuGet](https://img.shields.io/nuget/dt/commandlineparser.svg)](http://nuget.org/packages/commandlineparser)
[![NuGet](https://img.shields.io/nuget/v/commandlineparser.svg)](https://www.nuget.org/packages/CommandLineParser/)
[![NuGet](https://img.shields.io/nuget/vpre/commandlineparser.svg)](https://www.nuget.org/packages/CommandLineParser/)
[![Join the Gitter chat!](https://badges.gitter.im/gsscoder/commandline.svg)](https://gitter.im/gsscoder/commandline?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

# Command Line Parser Library for CLR and NetStandard

**Note:** the API surface has changed since v1.9.x and earlier. If you are looking for documentation on v1.9.x, please see [stable-1.9.71.2](https://github.com/gsscoder/commandline/tree/stable-1.9.71.2)

The Command Line Parser Library offers CLR applications a clean and concise API for manipulating command line arguments and related tasks, such as defining switches, options and verb commands. It allows you to display a help screen with a high degree of customization and a simple way to report syntax errors to the end user.

```
C:\Project> NuGet Install CommandLineParser
```

# Nightly Build

Nightly version of the CommandLineParser can be downloaded from github [Releases](https://github.com/commandlineparser/commandline/releases). 

The Last new features and fixes, read [changelog](https://github.com/commandlineparser/commandline/blob/master/CHANGELOG.md)


_NOTE: Mentioned F# Support is provided via ```CommandLineParser.FSharp``` package with FSharp dependencies._

__This library provides _hassle free_ command line parsing with a constantly updated API since 2005.__

# At a glance:

- Compatible with __.NET Framework 4.0+__, __Mono 2.1+ Profile__, __.NET Standard__ and __.NET Core__
- Doesn't depend on other packages (No dependencies beyond standard base libraries)
- One line parsing using default singleton: `CommandLine.Parser.Default.ParseArguments(...)` and three overload methods.
- Automatic or one line help screen generator: `HelpText.AutoBuild(...)`.
- Supports `--help`, `--version`, `version` and `help [verb]` by default with customization.
- Map to sequences (via `IEnumerable<T>` and similar) and scalar types, including Enums and `Nullable<T>`.
- You can also map to every type with a constructor that accepts a string (like `System.Uri`) for reference and value types.
- Verbs can be array of types collected from Plugins or IoC container.
- Define [verb commands](https://github.com/commandlineparser/commandline/wiki/Verbs) similar to `git commit -a`.
- Support default verb.
- Support Mutable and Immutable types.
- Support HelpText localization.
- Support ordering of options in HelpText.
- Support [Mutually Exclusive Options](https://github.com/commandlineparser/commandline/wiki/Mutually-Exclusive-Options) and [Option groups](https://github.com/commandlineparser/commandline/wiki/Option-Groups).
- Support named and value options.
- Support Asynchronous programming with async and await.
- Unparsing support: `CommandLine.Parser.Default.FormatCommandLine<T>(T options)`.
- CommandLineParser.FSharp package is F#-friendly with support for `option<'a>`, see [demo](https://github.com/commandlineparser/commandline/blob/master/demo/fsharp-demo.fsx).  _NOTE: This is a separate NuGet package._
- Include wiki documentation with lot of examples ready to run online.
- Support Source Link and symbolic nuget package snupkg.
- Tested in Windows, Linux Ubuntu 18.04 and Mac OS.
- Most of features applies with a [CoC](http://en.wikipedia.org/wiki/Convention_over_configuration) philosophy.
- C# demo: source [here](https://github.com/commandlineparser/commandline/tree/master/demo/ReadText.Demo).

# Getting Started with the Command Line Parser Library

You can utilize the parser library in several ways:

- Install via NuGet/Paket: [https://www.nuget.org/packages/CommandLineParser/](https://www.nuget.org/packages/CommandLineParser/)
- Integrate directly into your project by copying the .cs files into your project.
- ILMerge during your build process.

## Quick Start Examples

1. Create a class to define valid options, and to receive the parsed options.
2. Call ParseArguments with the args string array.

C# Quick Start:

```cs
using System;
using CommandLine;

namespace QuickStart
{
    class Program
    {
        public class Options
        {
            [Option('v', "verbose", Required = false, HelpText = "Set output to verbose messages.")]
            public bool Verbose { get; set; }
        }

        static void Main(string[] args)
        {
            Parser.Default.ParseArguments<Options>(args)
                   .WithParsed<Options>(o =>
                   {
                       if (o.Verbose)
                       {
                           Console.WriteLine($"Verbose output enabled. Current Arguments: -v {o.Verbose}");
                           Console.WriteLine("Quick Start Example! App is in Verbose mode!");
                       }
                       else
                       {
                           Console.WriteLine($"Current Arguments: -v {o.Verbose}");
                           Console.WriteLine("Quick Start Example!");
                       }
                   });
        }
    }
}
```

## C# Examples:

<details>
  <summary>Click to expand!</summary>

```cs

class Options
{
  [Option('r', "read", Required = true, HelpText = "Input files to be processed.")]
  public IEnumerable<string> InputFiles { get; set; }

  // Omitting long name, defaults to name of property, ie "--verbose"
  [Option(
	Default = false,
	HelpText = "Prints all messages to standard output.")]
  public bool Verbose { get; set; }
  
  [Option("stdin",
	Default = false,
	HelpText = "Read from stdin")]
  public bool stdin { get; set; }

  [Value(0, MetaName = "offset", HelpText = "File offset.")]
  public long? Offset { get; set; }
}

static void Main(string[] args)
{
  CommandLine.Parser.Default.ParseArguments<Options>(args)
    .WithParsed(RunOptions)
    .WithNotParsed(HandleParseError);
}
static void RunOptions(Options opts)
{
  //handle options
}
static void HandleParseError(IEnumerable<Error> errs)
{
  //handle errors
}

```

</details>

Demo to show IEnumerable  options and other usage:  [Online Demo](https://dotnetfiddle.net/wrcAxr)

## F# Examples:

<details>
  <summary>Click to expand!</summary>

```fsharp

type options = {
  [<Option('r', "read", Required = true, HelpText = "Input files.")>] files : seq<string>;
  [<Option(HelpText = "Prints all messages to standard output.")>] verbose : bool;
  [<Option(Default = "русский", HelpText = "Content language.")>] language : string;
  [<Value(0, MetaName="offset", HelpText = "File offset.")>] offset : int64 option;
}

let main argv =
  let result = CommandLine.Parser.Default.ParseArguments<options>(argv)
  match result with
  | :? Parsed<options> as parsed -> run parsed.Value
  | :? NotParsed<options> as notParsed -> fail notParsed.Errors
```
</details>

## VB.NET Example:

<details>
  <summary>Click to expand!</summary>

```vb

Class Options
	<CommandLine.Option('r', "read", Required := true,
	HelpText:="Input files to be processed.")>
	Public Property InputFiles As IEnumerable(Of String)

	' Omitting long name, defaults to name of property, ie "--verbose"
	<CommandLine.Option(
	HelpText:="Prints all messages to standard output.")>
	Public Property Verbose As Boolean

	<CommandLine.Option(Default:="中文",
	HelpText:="Content language.")>
	Public Property Language As String

	<CommandLine.Value(0, MetaName:="offset",
	HelpText:="File offset.")>
	Public Property Offset As Long?
End Class

Sub Main(ByVal args As String())
    CommandLine.Parser.Default.ParseArguments(Of Options)(args) _
        .WithParsed(Function(opts As Options) RunOptionsAndReturnExitCode(opts)) _
        .WithNotParsed(Function(errs As IEnumerable(Of [Error])) 1)
End Sub
```
</details>

## For verbs:

1. Create separate option classes for each verb.  An options base class is supported.  
2. Call ParseArguments with all the verb attribute decorated options classes.
3. Use MapResult to direct program flow to the verb that was parsed.

### C# example:


<details>
  <summary>Click to expand!</summary>

```csharp
[Verb("add", HelpText = "Add file contents to the index.")]
class AddOptions {
  //normal options here
}
[Verb("commit", HelpText = "Record changes to the repository.")]
class CommitOptions {
  //commit options here
}
[Verb("clone", HelpText = "Clone a repository into a new directory.")]
class CloneOptions {
  //clone options here
}

int Main(string[] args) {
  return CommandLine.Parser.Default.ParseArguments<AddOptions, CommitOptions, CloneOptions>(args)
	.MapResult(
	  (AddOptions opts) => RunAddAndReturnExitCode(opts),
	  (CommitOptions opts) => RunCommitAndReturnExitCode(opts),
	  (CloneOptions opts) => RunCloneAndReturnExitCode(opts),
	  errs => 1);
}
```
</details>

### VB.NET example:


<details>
  <summary>Click to expand!</summary>

```vb
<CommandLine.Verb("add", HelpText:="Add file contents to the index.")>
Public Class AddOptions
    'Normal options here
End Class
<CommandLine.Verb("commit", HelpText:="Record changes to the repository.")>
Public Class CommitOptions
    'Normal options here
End Class
<CommandLine.Verb("clone", HelpText:="Clone a repository into a new directory.")>
Public Class CloneOptions
    'Normal options here
End Class

Function Main(ByVal args As String()) As Integer
    Return CommandLine.Parser.Default.ParseArguments(Of AddOptions, CommitOptions, CloneOptions)(args) _
          .MapResult(
              (Function(opts As AddOptions) RunAddAndReturnExitCode(opts)),
              (Function(opts As CommitOptions) RunCommitAndReturnExitCode(opts)),
              (Function(opts As CloneOptions) RunCloneAndReturnExitCode(opts)),
              (Function(errs As IEnumerable(Of [Error])) 1)
          )
End Function
```
</details>

### F# Example:

<details>
  <summary>Click to expand!</summary>

```fs
open CommandLine

[<Verb("add", HelpText = "Add file contents to the index.")>]
type AddOptions = {
  // normal options here
}
[<Verb("commit", HelpText = "Record changes to the repository.")>]
type CommitOptions = {
  // normal options here
}
[<Verb("clone", HelpText = "Clone a repository into a new directory.")>]
type CloneOptions = {
  // normal options here
}

[<EntryPoint>]
let main args =
  let result = Parser.Default.ParseArguments<AddOptions, CommitOptions, CloneOptions> args
  match result with
  | :? CommandLine.Parsed<obj> as command ->
	match command.Value with
	| :? AddOptions as opts -> RunAddAndReturnExitCode opts
	| :? CommitOptions as opts -> RunCommitAndReturnExitCode opts
	| :? CloneOptions as opts -> RunCloneAndReturnExitCode opts
  | :? CommandLine.NotParsed<obj> -> 1
```
</details>

# Release History

See the [changelog](CHANGELOG.md)

# Contributors
First off, _Thank you!_  All contributions are welcome.  

Please consider sticking with the GNU getopt standard for command line parsing.  

Additionally, for easiest diff compares, please follow the project's tabs settings.  Utilizing the EditorConfig extension for Visual Studio/your favorite IDE is recommended.

__And most importantly, please target the ```develop``` branch in your pull requests!__

## Main Contributors (alphabetical order):
- Alexander Fast (@mizipzor)
- Dan Nemec (@nemec)
- Eric Newton (@ericnewton76)
- Kevin Moore (@gimmemoore)
- Moh-Hassan (@moh-hassan)
- Steven Evans
- Thomas Démoulins (@Thilas)

## Resources for newcomers:

- [Wiki](https://github.com/commandlineparser/commandline/wiki)
- [GNU getopt](http://www.gnu.org/software/libc/manual/html_node/Getopt.html)

# Contacts:

- Giacomo Stelluti Scala
  - gsscoder AT gmail DOT com (_use this for everything that is not available via GitHub features_)
  - GitHub: [gsscoder](https://github.com/gsscoder)
  - [Blog](http://gsscoder.blogspot.it)
  - [Twitter](http://twitter.com/gsscoder)
- Dan Nemec
- Eric Newton
  - ericnewton76+commandlineparser AT gmail DOT com
  - GitHub: [ericnewton76](https://github.com/ericnewton76)
  - Blog: 
  - Twitter: [enorl76](http://twitter.com/enorl76)
- Moh-Hassan 
