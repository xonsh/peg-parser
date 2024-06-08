use once_cell::sync::Lazy;
use regex::Regex;
use std::collections::HashMap;
use std::collections::HashSet;
use std::sync::Mutex;
use itertools::{Itertools}; // Import the Itertools library


pub fn capname<T: AsRef<str>>(name: T, pattern: T) -> String {
    format!("(?P<{}>{})", name.as_ref(), pattern.as_ref())
}


pub fn choice<T: AsRef<str>>(choices: &[T], named_choices: Option<&[(T, T)]>) -> String {
    let mut all_choices: Vec<String> = choices.iter().map(|c| c.as_ref().to_string()).collect();
    if let Some(named_choices) = named_choices {
        all_choices.extend(named_choices.into_iter().map(|(name, pattern)| capname(name, pattern)));
    }
    all_choices.join("|")
}

pub fn group<T: AsRef<str>>(choices: &[T], name: Option<T>, named_choices: Option<&[(T, T)]>) -> String {
    let pattern = format!("({})", choice(choices, named_choices));
    if let Some(name) = name {
        return capname(name.as_ref(), &pattern);
    }
    pattern
}

pub fn maybe<T: AsRef<str>>(choices: &[T]) -> String {
    format!("{}?", group(choices, None, None))
}


pub fn all_string_prefixes() -> Vec<String> {
    let valid_string_prefixes = vec!["b", "r", "u", "f", "br", "fr", "p", "pr", "pf"];
    let mut result = HashSet::new();
    result.insert(String::new());

    for prefix in valid_string_prefixes {
        for perm in prefix.chars().permutations(prefix.len()) {
            let perm: String = perm.into_iter().collect();
            for u in perm.chars().map(|c| vec![c.to_ascii_lowercase(), c.to_ascii_uppercase()]).multi_cartesian_product() {
                let combined: String = u.into_iter().collect();
                result.insert(combined);
            }
        }
    }

    result.into_iter().collect()
}

static COMPILED_REGEXES: Lazy<Mutex<HashMap<String, Regex>>> =
    Lazy::new(|| Mutex::new(HashMap::new()));

pub fn compile(expr: &str) -> Regex {
    let mut map = COMPILED_REGEXES.lock().unwrap();
    map.entry(expr.to_string())
        .or_insert_with(|| Regex::new(expr).unwrap())
        .clone()
}

// tests to debug choice and group
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_capname() {
        let name = "name";
        let pattern = "a";
        let result = capname(name, pattern);
        assert_eq!(result, "(?P<name>a)");
    }

    #[test]
    fn test_choice() {
        let choices = vec!["a", "b", "c"];
        let named_choices = vec![("name", "a"), ("name2", "b")];
        let pattern = choice(&choices, Some(&named_choices));
        assert_eq!(pattern, "a|b|c|(?P<name>a)|(?P<name2>b)");
    }

    #[test]
    fn test_group() {
        let choices = vec!["a", "b", "c"];
        let named_choices = vec![("name", "a"), ("name2", "b")];
        let pattern = group(&choices, Some("name"), Some(&named_choices));
        assert_eq!(pattern, "(?P<name>(a|b|c|(?P<name>a)|(?P<name2>b)))");
    }

    #[test]
    fn test_all_string_prefixes() {
        let result = all_string_prefixes().into_iter().collect::<Vec<String>>();
        assert_eq!(result.len(), 43);
    }
}
