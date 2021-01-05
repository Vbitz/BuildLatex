#!/usr/bin/env python3

"""
BuildLatex - Markdown to Latex Build Tool
By Joshua Scarsbrook
"""

import subprocess

from absl import app, flags, logging

import os
import re

# Directory Names
ROOT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))

THIRD_PARTY_DIRECTORY = os.path.join(ROOT_DIRECTORY, "third_party")

# Command Names
PANDOC = "pandoc"
LATEX = "xelatex"
BIBER = "biber"
BIBTEX = "bibtex"

# Command Line Flag Defintions
flags.DEFINE_bool(
    "pandoc", True, "Should Pandoc be used to convert Markdown into Latex")
flags.DEFINE_string("filename", None, "The markdown file to build.")
flags.DEFINE_string("metadata", None, "The metadata to pass into pandoc.")
flags.DEFINE_string(
    "template", None, "The template to use for building into latex.")
flags.DEFINE_multi_string(
    "part", None, "Single markdown files to compile. Happens instead of the regular filename handling but respects other arguments. Will not convert into .pdf.")
flags.DEFINE_string("part_output", None, "Output path for parts.")
flags.DEFINE_bool(
    "simple", None, "Automatically sets standalone, output_dir, and pretty for simple documents.")
flags.DEFINE_bool("standalone", False,
                  "Should a standalone latex file be built? Required for building a PDF")
flags.DEFINE_bool(
    "bibtex", False, "Should a bibliography be included? A filename should already be set in the metadata.")
flags.DEFINE_bool("biblatex", False, "Should bibtex be used insteed of biber?")
flags.DEFINE_bool("highlight", False, "Should syntax highlighting be enabled?")
flags.DEFINE_string("output_dir", None,
                    "What relative output directory be used for latex?")
flags.DEFINE_bool(
    "pretty", False, "Should geometry+font settings be set for a standalone document?")
flags.DEFINE_bool(
    "thesis", False, "Should geometry+font settings be set for a standalone thesis document (UQ Settings)?")
flags.DEFINE_bool("markdown_tex", True,
                  "Should markdown be allowed to contain tex commands.")

FLAGS = flags.FLAGS


def join_path(*args):
    return os.path.join(*args)


def shell_command(cmd: list, throw=True, output=False, shell=False, cwd=None):
    logging.info("shell_command %s", cmd)

    last_cwd = os.getcwd()

    if cwd != None:
        os.chdir(cwd)

    if throw:
        if output:
            return subprocess.check_output(cmd)
        elif shell:
            p = subprocess.Popen(cmd, shell=True)

            p.wait()
        else:
            subprocess.check_call(cmd)
    else:
        subprocess.call(cmd)

    if cwd != None:
        os.chdir(last_cwd)


def call_pandoc(filename: str, output_filename: str, output_type: str, *args):
    input_type = "markdown-raw_tex"

    if FLAGS.markdown_tex:
        logging.info("Using Markdown format instead of markdown-raw_tex")
        input_type = "markdown"

    pandoc_command = [PANDOC, *args, "-f", input_type, "-t",
                      output_type, "-o", output_filename, filename]

    shell_command(pandoc_command)


def process_metadata(filename: str):
    file_content = ""

    with open(filename, "r") as file_handle:
        file_content = file_handle.read()

    METADATA_REGEX = re.compile(
        "\\\\codeMetadata\\[([a-zA-Z0-9:]+)\\]{([\\w\\(\\):\. ]+)}[\\s\\n]+(\\\\begin{Shaded}[\\s\\S]*?\\\\end{Shaded})")

    REPLACEMENT = """
    \\begin{listing}
    %s\\label{%s}
    \\caption{%s}
    \\end{listing}
    """

    new_content = METADATA_REGEX.sub(lambda match: REPLACEMENT % (
        match[3], match[1], match[2]), file_content)

    with open(filename, "w") as file_handle:
        file_handle.write(new_content)


def convert_to_tex(filename: str):
    tex_filename = "%s.tex" % (filename,)
    md_filename = "%s.md" % (filename,)

    if FLAGS.part_output:
        tex_filename = "%s%s.tex" % (
            FLAGS.part_output, os.path.basename(filename))

    pandoc_args = []

    pandoc_args += ["--verbose"]

    if FLAGS.standalone:
        logging.info("Using standalone pandoc build.")

        pandoc_args += ["--standalone"]

    if FLAGS.bibtex:
        logging.info("Using biber & ieee.csl.")

        pandoc_args += ["--biblatex"]
        pandoc_args += ["--csl", join_path(THIRD_PARTY_DIRECTORY, "ieee.csl")]

    if FLAGS.biblatex:
        logging.info("Using bibtex insteed of biber")

    if FLAGS.thesis:
        logging.info("Using thesis-format flags.")

        pandoc_args += ["-V", "geometry:margin=20mm",
                        "-V", "mainfont:Times New Roman",
                        "-V", "papersize:a4",
                        "-V", "classoption:12pt"]

        if FLAGS.template == None:
            pandoc_args += ["--template", join_path(ROOT_DIRECTORY,
                                                    "thesis-template.tex")]

    if FLAGS.template != None:
        logging.info("Using template file %s", FLAGS.template)

        pandoc_args += ["--template", FLAGS.template]

    if FLAGS.metadata != None:
        logging.info("Using metadata file %s", FLAGS.metadata)

        pandoc_args += ["--metadata-file", FLAGS.metadata]

    if FLAGS.highlight:
        logging.info("Using custom syntax highlighter.")

        pandoc_args += [
            "--syntax-definition", join_path(THIRD_PARTY_DIRECTORY,
                                             "typescript.xml"),
            "--highlight=tango", ]

    if FLAGS.pretty:
        logging.info("Using pretty flags.")

        pandoc_args += ["-V", "geometry:margin=2cm",
                        "-V", "mainfont:Roboto",
                        "-V", "papersize:a4"]

    call_pandoc(md_filename, tex_filename, "latex", *pandoc_args)

    if FLAGS.highlight:
        process_metadata(tex_filename)


def build_pdf(filename: str):
    tex_filename = "%s.tex" % (filename,)

    latex_args = []

    if FLAGS.output_dir != None:
        latex_args += ["-output-directory=" + FLAGS.output_dir]

    latex_args += ["-interaction=nonstopmode"]

    shell_command([LATEX, *latex_args, tex_filename])

    if FLAGS.bibtex:
        if FLAGS.biblatex:
            shell_command([BIBTEX, filename])
        else:
            shell_command([BIBER, filename])

        shell_command([LATEX, *latex_args,  tex_filename])

    shell_command([LATEX, *latex_args,  tex_filename])


def main(args):
    logging.info("Building %s", FLAGS.filename)

    if FLAGS.simple:
        FLAGS.output_dir = os.path.dirname(FLAGS.filename)
        FLAGS.standalone = True
        if not FLAGS.thesis:
            FLAGS.pretty = True

    if FLAGS.part is not None and len(FLAGS.part) > 0:
        for part in FLAGS.part:
            logging.info("Building Part %s", part)
            convert_to_tex(part)
    else:
        if FLAGS.pandoc:
            convert_to_tex(FLAGS.filename)
        else:
            logging.info("Not invoking pandoc")

    build_pdf(FLAGS.filename)


if __name__ == "__main__":
    flags.mark_flag_as_required("filename")

    app.run(main)
