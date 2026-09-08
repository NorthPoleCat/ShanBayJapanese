package main

import (
	"flag"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
)

func run(root, script string) error {
	cmd := exec.Command("python3", filepath.Join(root, "scripts", script))
	cmd.Dir = root
	cmd.Stdout, cmd.Stderr, cmd.Stdin = os.Stdout, os.Stderr, os.Stdin
	return cmd.Run()
}

func main() {
	rootFlag := flag.String("root", ".", "builder root")
	sample := flag.Bool("sample", false, "build included sample DB")
	flag.Parse()
	root, _ := filepath.Abs(*rootFlag)

	if *sample {
		if err := run(root, "build_sample.py"); err != nil { panic(err) }
		return
	}

	for _, s := range []string{
		"download_sources.py","normalize_jlpt.py","parse_jmdict.py",
		"match_jmdict.py","export_zh_template.py",
	} {
		fmt.Println("==>", s)
		if err := run(root, s); err != nil { panic(err) }
	}
	fmt.Println("Fill data/intermediate/zh_meanings.csv, then run build_sqlite.py and validate.py.")
}
